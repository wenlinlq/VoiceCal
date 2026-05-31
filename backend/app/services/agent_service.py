import base64
import inspect
import json
import logging
import re
from contextvars import ContextVar
from typing import Any, Awaitable, Callable

from agentscope.agent import ReActAgent
from agentscope.formatter import DashScopeChatFormatter
from agentscope.message import Msg, TextBlock
from agentscope.model import DashScopeChatModel
from agentscope.tool import Toolkit, ToolResponse
from agentscope.tts import DashScopeRealtimeTTSModel, TTSModelBase

from app.core.config import settings
from app.services.memory_manager import memory_manager
from app.services.prompts import build_voice_calendar_system_prompt
from app.tools.calendar_tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)

def _clean_tts_text(text: str) -> str:
    """清洗 TTS 朗读文本：去除 emoji、Markdown 格式、多余空白。"""
    import re
    # 去除 emoji 和特殊符号（保留中文、字母、数字、标点、空格）
    text = re.sub(r'[^一-鿿　-〿＀-￯a-zA-Z0-9\s.,!?;:()（）【】《》""''、。，！？；：…—\-+]', '', text)
    # 去除 Markdown: **bold** *italic* `code`
    text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # 去除多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    return text

class _CleanTTSWrapper:
    """实时 TTS 包装器：在 push 文字之前清洗 emoji 和 Markdown，避免 TTS 朗读垃圾内容。"""

    def __init__(self, inner: DashScopeRealtimeTTSModel):
        self._inner = inner
        # 代理所有属性到内部模型
        self.model_name = inner.model_name
        self.stream = inner.stream
        self.supports_streaming_input = inner.supports_streaming_input

    async def push(self, msg, **kwargs):
        """清洗 msg 文本后再推给 TTS。"""
        import copy
        clean_msg = copy.copy(msg)
        # 清洗 text block 内容
        cleaned_blocks = []
        for block in (msg.content or []):
            if isinstance(block, dict):
                b = dict(block)
                if b.get("type") == "text" and "text" in b:
                    b["text"] = _clean_tts_text(b["text"])
                cleaned_blocks.append(b)
            else:
                cleaned_blocks.append(block)
        clean_msg.content = cleaned_blocks
        return await self._inner.push(clean_msg, **kwargs)

    async def synthesize(self, msg=None, **kwargs):
        if msg:
            import copy
            clean_msg = copy.copy(msg)
            cleaned_blocks = []
            for block in (msg.content or []):
                if isinstance(block, dict):
                    b = dict(block)
                    if b.get("type") == "text" and "text" in b:
                        b["text"] = _clean_tts_text(b["text"])
                    cleaned_blocks.append(b)
                else:
                    cleaned_blocks.append(block)
            clean_msg.content = cleaned_blocks
            return await self._inner.synthesize(clean_msg, **kwargs)
        return await self._inner.synthesize(msg, **kwargs)

    async def connect(self):
        return await self._inner.connect()

    async def close(self):
        return await self._inner.close()

    async def __aenter__(self):
        return await self._inner.__aenter__()

    async def __aexit__(self, *args):
        return await self._inner.__aexit__(*args)


_db_ctx: ContextVar[Any] = ContextVar("db_session")
_user_id_ctx: ContextVar[str] = ContextVar("user_id", default="")
_session_id_ctx: ContextVar[str] = ContextVar("session_id", default="")

WRITE_TOOL_NAMES = {"add_calendar_event", "create_reminder", "delete_calendar_event", "update_calendar_event"}
TIME_KEYWORDS = (
    "今天",
    "明天",
    "后天",
    "上午",
    "下午",
    "晚上",
    "早上",
    "点",
    "半小时后",
    "十分钟后",
    "两天后",
    "下周",
    "本周",
)
CREATE_KEYWORDS = ("提醒", "安排", "创建", "设置", "加", "有", "开会", "会议", "面试", "组会")
CONFIRM_WORDS = ("确认", "好的", "好", "行", "可以", "是的", "对", "嗯", "确定", "没问题", "要", "继续")


class CalendarAgentService:
    """基于 AgentScope ReActAgent 的主日历智能体服务。"""

    def __init__(self):
        self.model = DashScopeChatModel(
            api_key=settings.dashscope_api_key,
            model_name="qwen-plus",
            stream=True,
        )
        self.formatter = DashScopeChatFormatter()
        self.tts_model = _CleanTTSWrapper(DashScopeRealtimeTTSModel(
            api_key=settings.dashscope_api_key,
            model_name="qwen-tts-realtime",
        ))
        logger.info("[Agent] 初始化日历智能体完成")

    def _create_toolkit(self, db, user_id: str, tool_calls: list[dict[str, Any]] | None = None) -> Toolkit:
        toolkit = Toolkit()

        async def get_current_time() -> dict[str, Any]:
            return await TOOL_REGISTRY["get_current_time"](db, user_id, {})

        async def parse_datetime(text: str, current_time: str, timezone: str, duration_minutes: int | None = None) -> dict[str, Any]:
            args = {"text": text, "current_time": current_time, "timezone": timezone}
            if duration_minutes is not None:
                args["duration_minutes"] = duration_minutes
            return await TOOL_REGISTRY["parse_datetime"](db, user_id, args)

        async def query_calendar_events(start_time: str | None = None, end_time: str | None = None, keyword: str | None = None) -> dict[str, Any]:
            args: dict[str, Any] = {}
            if start_time is not None:
                args["start_time"] = start_time
            if end_time is not None:
                args["end_time"] = end_time
            if keyword is not None:
                args["keyword"] = keyword
            return await TOOL_REGISTRY["query_calendar_events"](db, user_id, args)

        async def check_time_conflict(start_time: str, end_time: str) -> dict[str, Any]:
            return await TOOL_REGISTRY["check_time_conflict"](db, user_id, {"start_time": start_time, "end_time": end_time})

        async def detect_duplicate_events(title: str, start_time: str, end_time: str) -> dict[str, Any]:
            return await TOOL_REGISTRY["detect_duplicate_events"](
                db,
                user_id,
                {"title": title, "start_time": start_time, "end_time": end_time},
            )

        async def suggest_available_slots(start_time: str, end_time: str, duration_minutes: int | None = None) -> dict[str, Any]:
            args: dict[str, Any] = {"start_time": start_time, "end_time": end_time}
            if duration_minutes is not None:
                args["duration_minutes"] = duration_minutes
            return await TOOL_REGISTRY["suggest_available_slots"](db, user_id, args)

        async def add_calendar_event(
            title: str,
            start_time: str,
            end_time: str,
            description: str | None = None,
            location: str | None = None,
            is_all_day: bool | None = None,
            force: bool | None = None,
            allow_past: bool | None = None,
            confirm: bool | None = None,
        ) -> dict[str, Any]:
            args: dict[str, Any] = {
                "title": title,
                "start_time": start_time,
                "end_time": end_time,
            }
            if description is not None:
                args["description"] = description
            if location is not None:
                args["location"] = location
            if is_all_day is not None:
                args["is_all_day"] = is_all_day
            if force is not None:
                args["force"] = force
            if allow_past is not None:
                args["allow_past"] = allow_past
            if confirm is not None:
                args["confirm"] = confirm
            return await TOOL_REGISTRY["add_calendar_event"](db, user_id, args)

        async def delete_calendar_event(event_id: str, confirm: bool | None = None) -> dict[str, Any]:
            args: dict[str, Any] = {"event_id": event_id}
            if confirm is not None:
                args["confirm"] = confirm
            return await TOOL_REGISTRY["delete_calendar_event"](db, user_id, args)

        async def update_calendar_event(
            event_id: str,
            title: str | None = None,
            description: str | None = None,
            location: str | None = None,
            start_time: str | None = None,
            end_time: str | None = None,
            is_all_day: bool | None = None,
            completed: bool | None = None,
            confirm: bool | None = None,
        ) -> dict[str, Any]:
            args: dict[str, Any] = {"event_id": event_id}
            if title is not None:
                args["title"] = title
            if description is not None:
                args["description"] = description
            if location is not None:
                args["location"] = location
            if start_time is not None:
                args["start_time"] = start_time
            if end_time is not None:
                args["end_time"] = end_time
            if is_all_day is not None:
                args["is_all_day"] = is_all_day
            if completed is not None:
                args["completed"] = completed
            if confirm is not None:
                args["confirm"] = confirm
            return await TOOL_REGISTRY["update_calendar_event"](db, user_id, args)

        async def get_event_by_id(event_id: str) -> dict[str, Any]:
            return await TOOL_REGISTRY["get_event_by_id"](db, user_id, {"event_id": event_id})

        async def create_reminder(
            start_time: str,
            end_time: str,
            title: str | None = None,
            description: str | None = None,
            location: str | None = None,
            force: bool | None = None,
            confirm: bool | None = None,
        ) -> dict[str, Any]:
            args: dict[str, Any] = {"start_time": start_time, "end_time": end_time}
            if title is not None:
                args["title"] = title
            if description is not None:
                args["description"] = description
            if location is not None:
                args["location"] = location
            if force is not None:
                args["force"] = force
            if confirm is not None:
                args["confirm"] = confirm
            return await TOOL_REGISTRY["create_reminder"](db, user_id, args)

        tool_functions = [
            get_current_time,
            parse_datetime,
            query_calendar_events,
            check_time_conflict,
            detect_duplicate_events,
            suggest_available_slots,
            add_calendar_event,
            delete_calendar_event,
            update_calendar_event,
            get_event_by_id,
            create_reminder,
        ]

        def _to_tool(fn):
            async def _wrapped(*args, **kwargs):
                result = await fn(*args, **kwargs)
                if tool_calls is not None:
                    tool_calls.append({"name": fn.__name__, "result": result})
                return ToolResponse(
                    content=[TextBlock(type="text", text=json.dumps(result, ensure_ascii=False))]
                )

            _wrapped.__name__ = fn.__name__
            return _wrapped

        for tool_fn in tool_functions:
            logger.info("[Agent] 注册工具 tool=%s", tool_fn.__name__)
            toolkit.register_tool_function(_to_tool(tool_fn))
        return toolkit

    def _looks_like_create_request(self, text: str) -> bool:
        normalized = text.replace(" ", "")
        return any(keyword in normalized for keyword in TIME_KEYWORDS) and any(
            keyword in normalized for keyword in CREATE_KEYWORDS
        )

    def _looks_like_reminder_request(self, text: str) -> bool:
        normalized = text.replace(" ", "")
        return "提醒" in normalized or "叫我" in normalized

    def _extract_title(self, text: str, is_reminder: bool) -> str:
        normalized = text.replace(" ", "")
        for keyword in ("项目会议", "技术面试", "七牛云面试", "组会", "面试", "会议", "开会"):
            if keyword in normalized:
                return "会议" if keyword == "开会" else keyword

        reminder_match = re.search(r"提醒我(.+?)(?:。|，|,|$)", normalized)
        if reminder_match:
            title = reminder_match.group(1).strip("一下啊呀")
            if title:
                return title

        return "提醒" if is_reminder else "日程"

    def _format_create_fallback_reply(self, tool_result: dict[str, Any], title: str, is_reminder: bool) -> str | None:
        if tool_result.get("success"):
            event = tool_result.get("data", {}).get("event", {})
            start_time = event.get("start_time", "")
            if "T" in start_time:
                hour_minute = start_time.split("T", 1)[1][:5]
                return f"好的，已为你设置{hour_minute}的{title}{'提醒' if is_reminder else ''}。"
            return f"好的，已为你设置{title}{'提醒' if is_reminder else ''}。"

        error_code = tool_result.get("error_code")
        data = tool_result.get("data") or {}
        if error_code == "TIME_CONFLICT" and data.get("conflicts"):
            conflict = data["conflicts"][0]
            return f"这个时间你已经有{conflict.get('title', '安排')}了，还要继续添加吗？"
        if error_code == "DUPLICATE_EVENT":
            return "这个提醒看起来已经存在了，我没有重复添加。"
        return None

    def _format_confirmation_reply(self, tool_calls: list[dict[str, Any]]) -> str | None:
        """
        当 Agent 最终输出不可靠（例如只输出“正在查询……”）时，
        从工具返回里兜底生成一条明确的“需要你确认/选择”的用户可读回复。
        """
        for call in reversed(tool_calls or []):
            result = call.get("result") or {}
            if result.get("success") is True:
                continue
            error_code = result.get("error_code")
            data = result.get("data") or {}

            if error_code == "CONFIRM_REQUIRED":
                preview = data.get("preview") or {}
                title = preview.get("title") or "这条日程"
                start_time = (preview.get("start_time") or "").replace("T", " ")
                end_time = (preview.get("end_time") or "").replace("T", " ")
                if start_time and end_time:
                    return f"我准备创建「{title}」（{start_time} - {end_time}），确认创建吗？"
                return f"我准备创建「{title}」，确认创建吗？"

            if error_code == "TIME_CONFLICT":
                conflicts = data.get("conflicts") or []
                if conflicts:
                    conflict = conflicts[0]
                    return f"这个时间你已经有{conflict.get('title', '安排')}了，还要继续添加吗？"
                return "这个时间段已经有安排了，还要继续添加吗？"

            if error_code == "DUPLICATE_EVENT":
                return "这个提醒看起来已经存在了，我没有重复添加。"

        return None

    async def _ensure_create_persisted(
        self,
        db,
        user_id: str,
        text: str,
        tool_calls: list[dict[str, Any]],
        skip_confirm: bool = False,
    ) -> str | None:
        if any(call["name"] in WRITE_TOOL_NAMES for call in tool_calls):
            return None
        if not self._looks_like_create_request(text):
            return None

        current_time_result = await TOOL_REGISTRY["get_current_time"](db, user_id, {})
        if not current_time_result.get("success"):
            return None

        current_time_data = current_time_result.get("data") or {}
        parsed_result = await TOOL_REGISTRY["parse_datetime"](
            db,
            user_id,
            {
                "text": text,
                "current_time": current_time_data.get("current_time"),
                "timezone": current_time_data.get("timezone", "Asia/Shanghai"),
            },
        )
        parsed_data = parsed_result.get("data") or {}
        if not parsed_result.get("success") or not parsed_data.get("is_complete"):
            return None

        is_reminder = self._looks_like_reminder_request(text)
        title = self._extract_title(text, is_reminder)
        args = {
            "title": title,
            "start_time": parsed_data["start_time"],
            "end_time": parsed_data["end_time"],
            "description": f"用户原始输入：{text}",
        }
        if skip_confirm:
            args["confirm"] = True  # 用户已在前一轮确认过
        tool_name = "create_reminder" if is_reminder else "add_calendar_event"
        tool_result = await TOOL_REGISTRY[tool_name](db, user_id, args)
        tool_calls.append({"name": tool_name, "result": tool_result, "fallback": True})
        logger.warning("[Agent] 兜底执行落库 tool=%s result=%s", tool_name, tool_result)
        return self._format_create_fallback_reply(tool_result, title, is_reminder)

    async def handle_text(
        self,
        db,
        user_id: str,
        text: str,
        session_id: str = "",
        on_speech_chunk: Callable[[bytes, bool], Awaitable[None]] | None = None,
    ) -> dict[str, Any]:
        _db_ctx.set(db)
        _user_id_ctx.set(user_id)
        _session_id_ctx.set(session_id or "")

        logger.info(
            "[Agent] 收到用户文本 session_id=%s user_id=%s 文本=%s",
            session_id,
            user_id,
            text[:200],
        )

        short_term_memory = await memory_manager.create_short_term_memory(user_id, session_id or user_id)
        long_term_memory = await memory_manager.create_long_term_memory(user_id)
        logger.info("[Agent] 已初始化短期与长期记忆 user_id=%s session_id=%s", user_id, session_id)

        session_key = session_id or user_id
        session_state = None
        try:
            from app.services.session_service import session_service

            session_state = await session_service.update_last_interaction(
                session_key,
                last_user_text=text,
            )
        except Exception:
            logger.exception("[Agent] 更新 session_state 失败 session_id=%s", session_key)

        if session_state is not None:
            logger.info("[Agent] 当前 session_state=%s", session_state)

        # ── Skill Router 快速路径 ──
        from app.services.skill_router import route_with_skill

        skill_result = await route_with_skill(db, user_id, text, self.model)
        if skill_result is not None:
            logger.info("[Agent] Skill 命中，跳过 ReActAgent")
            return {
                "reply_text": skill_result["reply_text"],
                "speech": None,
                "raw_msg": None,
                "need_confirm": skill_result.get("need_confirm", False),
                "speech_streamed": False,
            }

        tool_calls: list[dict[str, Any]] = []
        toolkit = self._create_toolkit(db, user_id, tool_calls)
        agent = ReActAgent(
            name="VoiceCalendarAgent",
            sys_prompt=build_voice_calendar_system_prompt(),
            model=self.model,
            formatter=self.formatter,
            toolkit=toolkit,
            memory=short_term_memory,
            long_term_memory=long_term_memory,
            long_term_memory_mode="agent_control",
            enable_rewrite_query=False,
            tts_model=self.tts_model,
            max_iters=5,
        )

        # WebSocket 服务端只需要把 TTS 音频分片转发给前端，不应在云端容器内尝试本地播放。
        def _discard_local_audio_playback(msg_id: str, audio_block) -> None:
            logger.debug("[Agent] 跳过服务端本地音频播放 msg_id=%s", msg_id)

        agent._process_audio_block = _discard_local_audio_playback  # type: ignore[attr-defined]

        speech_events: list[list[bytes]] = []  # 非流式路径下，每次 post_print 一个事件
        streamed_speech = False
        audio_prefix_by_msg: dict[str, list[str]] = {}

        async def _stream_agent_audio(chunk: bytes, is_last: bool) -> None:
            nonlocal streamed_speech
            if on_speech_chunk is None:
                return
            await on_speech_chunk(chunk, is_last)
            streamed_speech = True

        def _extract_incremental_audio_chunks(msg_id: str, speech_blocks) -> list[bytes]:
            blocks = speech_blocks if isinstance(speech_blocks, list) else [speech_blocks]
            prefixes = audio_prefix_by_msg.setdefault(msg_id, [])
            chunks: list[bytes] = []

            for index, block in enumerate(blocks):
                if not isinstance(block, dict) or "source" not in block:
                    continue

                source = block["source"] or {}
                if source.get("type") != "base64":
                    continue

                data = source.get("data", "")
                if not data:
                    continue

                while len(prefixes) <= index:
                    prefixes.append("")

                previous_data = prefixes[index]
                if previous_data and data.startswith(previous_data):
                    new_data = data[len(previous_data):]
                elif data == previous_data:
                    new_data = ""
                else:
                    logger.debug(
                        "[Agent] 检测到音频流前缀重置 msg_id=%s block=%s old_len=%s new_len=%s",
                        msg_id,
                        index,
                        len(previous_data),
                        len(data),
                    )
                    new_data = data

                prefixes[index] = data

                if new_data:
                    chunks.append(base64.b64decode(new_data))

            return chunks

        async def _on_post_print(agent_obj, print_kwargs, output):
            speech = print_kwargs.get("speech") if isinstance(print_kwargs, dict) else None
            if speech:
                msg = print_kwargs.get("msg") if isinstance(print_kwargs, dict) else None
                msg_id = getattr(msg, "id", "") or "unknown"
                chunks = _extract_incremental_audio_chunks(msg_id, speech)
                if chunks:
                    is_last_event = bool(print_kwargs.get("last")) if isinstance(print_kwargs, dict) else False
                    if on_speech_chunk is not None:
                        for index, chunk in enumerate(chunks):
                            is_last_chunk = is_last_event and (index == len(chunks) - 1)
                            await _stream_agent_audio(chunk, is_last_chunk)
                    else:
                        speech_events.append(chunks)
                        # 只保留最后 3 次语音输出，丢弃更早的中间过程
                        if len(speech_events) > 3:
                            speech_events.pop(0)
                elif on_speech_chunk is not None and bool(print_kwargs.get("last")):
                    await on_speech_chunk(b"", True)
                    streamed_speech = True

        hook_result = agent.register_instance_hook("post_print", "capture_speech", _on_post_print)
        if inspect.isawaitable(hook_result):
            await hook_result

        user_msg = Msg(name="User", content=text, role="user")
        result_msg = await agent(user_msg)
        reply_text = result_msg.get_text_content() or ""

        # 检测用户是否在进行确认回复（"确认""好的""行"等短句）
        is_confirm_followup = text.strip() in CONFIRM_WORDS or (
            len(text.strip()) <= 3 and any(w in text.strip() for w in CONFIRM_WORDS)
        )
        fallback_reply = await self._ensure_create_persisted(
            db, user_id, text, tool_calls,
            skip_confirm=is_confirm_followup,
        )
        if fallback_reply:
            reply_text = fallback_reply

        # 检测是否需要用户确认：
        # - CONFIRM_REQUIRED: 写操作首次调用必须确认
        # - TIME_CONFLICT / DUPLICATE_EVENT: 需要用户确认后用 force=True 重试
        confirm_error_codes = {"CONFIRM_REQUIRED", "TIME_CONFLICT", "DUPLICATE_EVENT"}

        # 如果 Agent 最终只输出了过程性话术（如“正在查询……”），但工具侧已经明确给出了
        # 需要用户确认/选择的结果，则用工具结果兜底生成一句可交互的回复。
        has_confirming_tool_result = any(
            (call.get("result") or {}).get("error_code") in confirm_error_codes
            for call in tool_calls
        )
        cleaned_reply = _clean_tts_text(reply_text.strip())
        looks_like_progress = (not cleaned_reply) or cleaned_reply.endswith(("…", "...", "……"))
        if has_confirming_tool_result and looks_like_progress:
            tool_fallback_reply = self._format_confirmation_reply(tool_calls)
            if tool_fallback_reply:
                reply_text = tool_fallback_reply

        need_confirm = any(
            call.get("result", {}).get("error_code") in confirm_error_codes
            for call in tool_calls
        )

        logger.info("[Agent] 最终回复 session_id=%s 文本=%s need_confirm=%s", session_id, reply_text[:200], need_confirm)

        # 安全网：need_confirm=True 但 agent 回复了完成语，强制纠正
        _completion_keywords = (
            "已为你",
            "已经为你",
            "已设置",
            "已安排",
            "已创建",
            "已删除",
            "已修改",
            "已添加",
            "已取消",
            "帮你安排",
            "帮你设置",
        )
        _looks_like_question = ("？" in reply_text) or ("?" in reply_text)
        if need_confirm and (not _looks_like_question) and any(kw in reply_text for kw in _completion_keywords):
            preview_info = next(
                (call.get("result", {}).get("data", {}).get("preview", {})
                 for call in tool_calls
                 if call.get("result", {}).get("error_code") == "CONFIRM_REQUIRED"),
                {},
            )
            title = preview_info.get("title", "此日程")
            logger.warning("[Agent] need_confirm=True 但回复包含完成语，强制替换为确认提问")
            reply_text = f"确认{title}吗？"

        lower_text = text.strip().lower()
        if any(keyword in lower_text for keyword in ("仍然添加", "就这个", "第一个", "取消吧", "改到四点", "换到四点")):
            logger.info("[Agent] 检测到多轮确认短句 session_id=%s 文本=%s", session_id, text)
            try:
                from app.services.session_service import session_service

                await session_service.update_last_interaction(
                    session_key,
                    last_user_text=text,
                    last_user_intent="multi_turn_followup",
                )
            except Exception:
                logger.exception("[Agent] 更新多轮确认状态失败 session_id=%s", session_key)

        # 合并所有语音事件为扁平列表
        all_speech_chunks: list[bytes] = [chunk for event in speech_events for chunk in event]

        if all_speech_chunks:
            logger.info(
                "[Agent] 语音事件数=%s 语音分片数=%s 总字节=%s",
                len(speech_events),
                len(all_speech_chunks),
                sum(len(chunk) for chunk in all_speech_chunks),
            )

        return {
            "reply_text": reply_text,
            "speech": None if streamed_speech else (all_speech_chunks if all_speech_chunks else None),
            "speech_streamed": streamed_speech,
            "need_confirm": need_confirm,
        }
