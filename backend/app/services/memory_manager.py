import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlparse

from agentscope.embedding import DashScopeTextEmbedding
from agentscope.memory import InMemoryMemory, LongTermMemoryBase, MemoryBase, Mem0LongTermMemory, RedisMemory
from agentscope.message import Msg, TextBlock
from agentscope.model import DashScopeChatModel
from agentscope.tool import ToolResponse
from mem0.vector_stores.configs import VectorStoreConfig

from app.core.config import settings

logger = logging.getLogger(__name__)


def _shorten(value: Any, limit: int = 160) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    text = text.strip()
    return text if len(text) <= limit else text[:limit] + "...[已截断]"


def _parse_redis_url(redis_url: str) -> dict[str, Any]:
    parsed = urlparse(redis_url)
    if parsed.scheme not in {"redis", "rediss"}:
        raise ValueError(f"不支持的 Redis 地址：{redis_url}")

    db_index = 0
    if parsed.path and parsed.path != "/":
        try:
            db_index = int(parsed.path.lstrip("/"))
        except ValueError:
            db_index = 0

    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 6379,
        "db": db_index,
        "password": parsed.password,
    }


@dataclass
class MemoryBundle:
    short_term_memory: MemoryBase
    long_term_memory: LongTermMemoryBase | None


class LoggingMemory(MemoryBase):
    def __init__(self, inner: MemoryBase, user_id: str, session_id: str):
        super().__init__()
        self.inner = inner
        self.user_id = user_id
        self.session_id = session_id

    async def add(self, memories: Msg | list[Msg] | None, marks: str | list[str] | None = None, **kwargs: Any) -> None:
        count = 0
        sample = ""
        if memories is None:
            count = 0
        elif isinstance(memories, Msg):
            count = 1
            sample = _shorten(memories.content)
        else:
            count = len(memories)
            sample = _shorten([msg.content for msg in memories[:2] if msg is not None])
        logger.info(
            "[记忆模块] 短期记忆写入消息，user_id=%s, session_id=%s, count=%s, marks=%s, sample=%s",
            self.user_id,
            self.session_id,
            count,
            marks,
            sample,
        )
        try:
            await self.inner.add(memories, marks=marks, **kwargs)
        except Exception as exc:
            logger.warning("[记忆模块] RedisMemory 写入失败，已降级为 InMemoryMemory，仅当前进程有效：%s", exc)
            self.inner = InMemoryMemory()
            await self.inner.add(memories, marks=marks, **kwargs)

    async def delete(self, msg_ids: list[str], **kwargs: Any) -> int:
        return await self.inner.delete(msg_ids, **kwargs)

    async def delete_by_mark(self, mark: str | list[str], *args: Any, **kwargs: Any) -> int:
        return await self.inner.delete_by_mark(mark, *args, **kwargs)

    async def size(self) -> int:
        try:
            return await self.inner.size()
        except Exception as exc:
            logger.warning("[记忆模块] RedisMemory 读取大小失败，已降级为 InMemoryMemory：%s", exc)
            self.inner = InMemoryMemory()
            return await self.inner.size()

    async def clear(self) -> None:
        logger.info(
            "[记忆模块] 清空短期记忆，user_id=%s, session_id=%s",
            self.user_id,
            self.session_id,
        )
        try:
            await self.inner.clear()
        except Exception as exc:
            logger.warning("[记忆模块] RedisMemory 清理失败，已降级为 InMemoryMemory：%s", exc)
            self.inner = InMemoryMemory()

    async def get_memory(
        self,
        mark: str | None = None,
        exclude_mark: str | None = None,
        prepend_summary: bool = True,
        **kwargs: Any,
    ) -> list[Msg]:
        logger.info(
            "[记忆模块] 读取短期记忆，user_id=%s, session_id=%s, mark=%s, exclude_mark=%s",
            self.user_id,
            self.session_id,
            mark,
            exclude_mark,
        )
        try:
            return await self.inner.get_memory(
                mark=mark,
                exclude_mark=exclude_mark,
                prepend_summary=prepend_summary,
                **kwargs,
            )
        except Exception as exc:
            logger.warning("[记忆模块] RedisMemory 读取上下文失败，已降级为 InMemoryMemory：%s", exc)
            self.inner = InMemoryMemory()
            return await self.inner.get_memory(
                mark=mark,
                exclude_mark=exclude_mark,
                prepend_summary=prepend_summary,
                **kwargs,
            )

    async def update_messages_mark(
        self,
        new_mark: str | None,
        old_mark: str | None = None,
        msg_ids: list[str] | None = None,
    ) -> int:
        return await self.inner.update_messages_mark(new_mark, old_mark=old_mark, msg_ids=msg_ids)

    async def update_compressed_summary(self, summary: str) -> None:
        await self.inner.update_compressed_summary(summary)

    async def close(self) -> None:
        close_fn = getattr(self.inner, "close", None)
        if callable(close_fn):
            await close_fn()


class VoiceCalendarLongTermMemory(LongTermMemoryBase):
    def __init__(self, inner: LongTermMemoryBase | None, user_id: str):
        super().__init__()
        self.inner = inner
        self.user_id = user_id

    async def _with_timeout(self, action: str, coro):
        timeout_seconds = max(1, int(settings.memory_long_term_timeout_seconds))
        try:
            return await asyncio.wait_for(coro, timeout=timeout_seconds)
        except asyncio.TimeoutError:
            logger.warning(
                "[长期记忆] %s 超时已跳过，user_id=%s timeout=%ss",
                action,
                self.user_id,
                timeout_seconds,
            )
            return None

    async def record(self, msgs: list[Msg | None], **kwargs: Any) -> Any:
        if self.inner is None:
            logger.info("[长期记忆] 跳过写入，长期记忆未启用，user_id=%s", self.user_id)
            return {}
        logger.info(
            "[长期记忆] 准备写入长期记忆，user_id=%s, content=%s",
            self.user_id,
            _shorten([msg.to_dict() for msg in msgs if msg is not None], 200),
        )
        try:
            result = await self._with_timeout("record", self.inner.record(msgs, **kwargs))
            logger.info("[长期记忆] 写入成功，user_id=%s", self.user_id)
            return result or {}
        except Exception as exc:
            logger.warning("[长期记忆] 写入失败：%s", exc)
            return {}

    async def retrieve(self, msg: Msg | list[Msg] | None, limit: int = 5, **kwargs: Any) -> str:
        if self.inner is None:
            logger.info("[长期记忆] 跳过检索，长期记忆未启用，user_id=%s", self.user_id)
            return ""
        logger.info(
            "[长期记忆] 准备检索长期记忆，user_id=%s, query=%s",
            self.user_id,
            _shorten([item.to_dict() for item in msg] if isinstance(msg, list) else msg.to_dict() if isinstance(msg, Msg) else ""),
        )
        try:
            result = await self._with_timeout("retrieve", self.inner.retrieve(msg, limit=limit, **kwargs))
            logger.info("[长期记忆] 检索结果：%s", _shorten(result, 200))
            if result:
                logger.info("[Agent] 已结合长期记忆补全日程参数")
            return result or ""
        except Exception as exc:
            logger.warning("[长期记忆] 检索失败：%s", exc)
            return ""

    async def record_to_memory(self, thinking: str, content: list[str], **kwargs: Any) -> ToolResponse:
        if self.inner is None:
            logger.info("[长期记忆] 写入被跳过，长期记忆未启用，user_id=%s, content=%s", self.user_id, content)
            return ToolResponse(content=[TextBlock(type="text", text="")])
        logger.info(
            "[长期记忆] 准备写入长期记忆，user_id=%s, thinking=%s, content=%s",
            self.user_id,
            _shorten(thinking),
            _shorten(content),
        )
        try:
            result = await self._with_timeout(
                "record_to_memory",
                self.inner.record_to_memory(thinking, content, **kwargs),
            )
            logger.info("[长期记忆] 写入成功，user_id=%s", self.user_id)
            return result or ToolResponse(content=[TextBlock(type="text", text="")])
        except Exception as exc:
            logger.warning("[长期记忆] 写入失败：%s", exc)
            return ToolResponse(content=[TextBlock(type="text", text=f"Error recording memory: {exc}")])

    async def retrieve_from_memory(self, keywords: list[str], limit: int = 5, **kwargs: Any) -> ToolResponse:
        if self.inner is None:
            logger.info("[长期记忆] 检索被跳过，长期记忆未启用，user_id=%s, keywords=%s", self.user_id, keywords)
            return ToolResponse(content=[TextBlock(type="text", text="")])
        logger.info(
            "[长期记忆] 准备检索长期记忆，user_id=%s, keywords=%s",
            self.user_id,
            keywords,
        )
        try:
            result = await self._with_timeout(
                "retrieve_from_memory",
                self.inner.retrieve_from_memory(keywords, limit=limit, **kwargs),
            )
            if result is None:
                return ToolResponse(content=[TextBlock(type="text", text="")])
            text = result.content[0].text if result.content else ""
            logger.info("[长期记忆] 检索结果：%s", _shorten(text, 200))
            if text:
                logger.info("[Agent] 已结合长期记忆补全日程参数")
            return result
        except Exception as exc:
            logger.warning("[长期记忆] 检索失败：%s", exc)
            return ToolResponse(content=[TextBlock(type="text", text=f"Error retrieving memory: {exc}")])


class VoiceCalendarMemoryManager:
    def __init__(self):
        self._redis_error_logged = False
        self._mem0_error_logged = False
        self._fallback_short_term: dict[tuple[str, str], InMemoryMemory] = {}
        self._long_term_cache: dict[str, LongTermMemoryBase] = {}

    def _get_fallback_short_term(self, user_id: str, session_id: str) -> InMemoryMemory:
        key = (user_id, session_id)
        if key not in self._fallback_short_term:
            self._fallback_short_term[key] = InMemoryMemory()
        return self._fallback_short_term[key]

    def _build_vector_store_config(self) -> VectorStoreConfig | None:
        provider = settings.mem0_vector_store.strip().lower()
        if not provider:
            logger.info("[长期记忆] 未指定向量存储，使用 Mem0 默认配置")
            return None

        if provider != "milvus":
            logger.info("[长期记忆] 使用自定义向量存储 provider=%s", provider)
            return VectorStoreConfig(provider=provider)

        logger.info(
            "[长期记忆] 正在配置 Milvus，url=%s, collection=%s, db_name=%s, dims=%s, metric=%s",
            settings.milvus_url,
            settings.milvus_collection_name,
            settings.milvus_db_name or "<default>",
            settings.milvus_embedding_dims,
            settings.milvus_metric_type,
        )
        return VectorStoreConfig(
            provider="milvus",
            config={
                "url": settings.milvus_url,
                "token": settings.milvus_token,
                "db_name": settings.milvus_db_name,
                "collection_name": settings.milvus_collection_name,
                "embedding_model_dims": settings.milvus_embedding_dims,
                "metric_type": settings.milvus_metric_type,
            },
        )

    async def create_short_term_memory(self, user_id: str, session_id: str) -> MemoryBase:
        logger.info("[记忆模块] 初始化 Redis 短期记忆，user_id=%s, session_id=%s", user_id, session_id)
        try:
            redis_params = _parse_redis_url(settings.redis_url)
            inner = RedisMemory(
                session_id=session_id,
                user_id=user_id,
                key_prefix=f"{settings.memory_key_prefix}:",
                key_ttl=settings.memory_short_ttl_seconds,
                **redis_params,
            )
            await inner.size()
            logger.info("[记忆模块] RedisMemory 初始化成功，user_id=%s, session_id=%s", user_id, session_id)
            return LoggingMemory(inner, user_id, session_id)
        except Exception as exc:
            if not self._redis_error_logged:
                logger.warning(
                    "[记忆模块] Redis 连接失败，已降级为 InMemoryMemory，仅当前进程有效：%s",
                    exc,
                )
                self._redis_error_logged = True
            return LoggingMemory(self._get_fallback_short_term(user_id, session_id), user_id, session_id)

    async def create_long_term_memory(self, user_id: str) -> LongTermMemoryBase | None:
        if user_id in self._long_term_cache:
            logger.info("[长期记忆] 复用 Mem0LongTermMemory，user_id=%s", user_id)
            return self._long_term_cache[user_id]

        logger.info("[长期记忆] 初始化 Mem0LongTermMemory，user_id=%s", user_id)
        if not settings.dashscope_api_key:
            logger.warning(
                "[长期记忆] DashScope API Key 未配置，embedding 初始化失败，已跳过长期记忆能力，user_id=%s",
                user_id,
            )
            return None

        try:
            import importlib.util

            if importlib.util.find_spec("mem0") is None:
                raise ImportError("mem0 package not installed")

            chat_model = DashScopeChatModel(
                api_key=settings.dashscope_api_key,
                model_name=settings.memory_llm_model,
                stream=False,
            )
            embedding_model = DashScopeTextEmbedding(
                api_key=settings.dashscope_api_key,
                model_name=settings.memory_embedding_model,
            )
            vector_store_config = self._build_vector_store_config()
            inner = Mem0LongTermMemory(
                agent_name=settings.memory_agent_name,
                user_name=user_id,
                model=chat_model,
                embedding_model=embedding_model,
                vector_store_config=vector_store_config,
                on_disk=settings.mem0_on_disk,
            )
            logger.info(
                "[长期记忆] Mem0LongTermMemory 初始化成功，user_id=%s, vector_store=%s",
                user_id,
                settings.mem0_vector_store or "default",
            )
            wrapped = VoiceCalendarLongTermMemory(inner, user_id)
            self._long_term_cache[user_id] = wrapped
            return wrapped
        except Exception as exc:
            if not self._mem0_error_logged:
                logger.warning("[长期记忆] Mem0 初始化失败，已跳过长期记忆能力：%s", exc)
                self._mem0_error_logged = True
            return None

    async def close_short_term_memory(self, memory: MemoryBase | None) -> None:
        if memory is None:
            return
        close_fn = getattr(memory, "close", None)
        if callable(close_fn):
            await close_fn()


memory_manager = VoiceCalendarMemoryManager()
