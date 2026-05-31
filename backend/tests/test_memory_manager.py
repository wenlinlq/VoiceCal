import importlib.util
import asyncio

import pytest

from app.services import memory_manager as memory_module
from app.services.memory_manager import VoiceCalendarMemoryManager, VoiceCalendarLongTermMemory


class DummyRedisMemory:
    created = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.messages = []
        DummyRedisMemory.created.append(kwargs)

    async def add(self, memories, marks=None, **kwargs):
        self.messages.append((memories, marks))

    async def delete(self, msg_ids, **kwargs):
        return 0

    async def delete_by_mark(self, mark, *args, **kwargs):
        return 0

    async def size(self):
        return len(self.messages)

    async def clear(self):
        self.messages.clear()

    async def get_memory(self, **kwargs):
        return []

    async def update_messages_mark(self, new_mark, old_mark=None, msg_ids=None):
        return 0

    async def update_compressed_summary(self, summary):
        return None

    async def close(self):
        return None


class DummyMem0LongTermMemory:
    created = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        DummyMem0LongTermMemory.created.append(kwargs)

    async def record(self, msgs, **kwargs):
        return {"ok": True}

    async def retrieve(self, msg, limit=5, **kwargs):
        return "用户的会议默认提醒时间是提前 30 分钟。"

    async def record_to_memory(self, thinking, content, **kwargs):
        return {"ok": True}

    async def retrieve_from_memory(self, keywords, limit=5, **kwargs):
        return {"ok": True}


@pytest.mark.asyncio
async def test_create_short_term_memory_uses_redis_namespace(monkeypatch):
    DummyRedisMemory.created.clear()
    manager = VoiceCalendarMemoryManager()
    monkeypatch.setattr(memory_module, "RedisMemory", DummyRedisMemory)
    monkeypatch.setattr(memory_module.settings, "redis_url", "redis://:pass@localhost:6380/2")
    monkeypatch.setattr(memory_module.settings, "memory_key_prefix", "voice_calendar")
    monkeypatch.setattr(memory_module.settings, "memory_short_ttl_seconds", 86400)

    memory = await manager.create_short_term_memory("user_a", "sess_a")

    assert await memory.size() == 0
    assert DummyRedisMemory.created[0]["user_id"] == "user_a"
    assert DummyRedisMemory.created[0]["session_id"] == "sess_a"
    assert DummyRedisMemory.created[0]["key_prefix"] == "voice_calendar:"
    assert DummyRedisMemory.created[0]["key_ttl"] == 86400
    assert DummyRedisMemory.created[0]["db"] == 2


@pytest.mark.asyncio
async def test_create_short_term_memory_falls_back_and_reuses_in_memory(monkeypatch):
    manager = VoiceCalendarMemoryManager()

    class BrokenRedisMemory:
        def __init__(self, **kwargs):
            raise RuntimeError("redis down")

    monkeypatch.setattr(memory_module, "RedisMemory", BrokenRedisMemory)

    first = await manager.create_short_term_memory("user_a", "sess_a")
    second = await manager.create_short_term_memory("user_a", "sess_a")
    other_user = await manager.create_short_term_memory("user_b", "sess_a")

    assert first.inner is second.inner
    assert first.inner is not other_user.inner


@pytest.mark.asyncio
async def test_create_long_term_memory_uses_mem0_user_scope(monkeypatch):
    DummyMem0LongTermMemory.created.clear()
    manager = VoiceCalendarMemoryManager()
    monkeypatch.setattr(memory_module.settings, "dashscope_api_key", "dashscope-key")
    monkeypatch.setattr(memory_module.settings, "memory_agent_name", "VoiceCalendarAgent")
    monkeypatch.setattr(memory_module.settings, "memory_llm_model", "qwen3.7-max")
    monkeypatch.setattr(memory_module.settings, "memory_embedding_model", "text-embedding-v3")
    monkeypatch.setattr(memory_module.settings, "mem0_vector_store", "milvus")
    monkeypatch.setattr(memory_module.settings, "mem0_on_disk", False)
    monkeypatch.setattr(memory_module.settings, "milvus_url", "http://localhost:19531")
    monkeypatch.setattr(memory_module.settings, "milvus_token", "")
    monkeypatch.setattr(memory_module.settings, "milvus_db_name", "")
    monkeypatch.setattr(memory_module.settings, "milvus_collection_name", "voice_calendar_memories")
    monkeypatch.setattr(memory_module.settings, "milvus_embedding_dims", 1024)
    monkeypatch.setattr(memory_module.settings, "milvus_metric_type", "COSINE")
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object() if name == "mem0" else None)
    monkeypatch.setattr(memory_module, "DashScopeChatModel", lambda **kwargs: {"chat": kwargs})
    monkeypatch.setattr(memory_module, "DashScopeTextEmbedding", lambda **kwargs: {"embedding": kwargs})
    monkeypatch.setattr(memory_module, "Mem0LongTermMemory", DummyMem0LongTermMemory)

    memory = await manager.create_long_term_memory("user_a")
    cached = await manager.create_long_term_memory("user_a")

    assert isinstance(memory, VoiceCalendarLongTermMemory)
    assert memory is cached
    assert DummyMem0LongTermMemory.created[0]["agent_name"] == "VoiceCalendarAgent"
    assert DummyMem0LongTermMemory.created[0]["user_name"] == "user_a"
    assert DummyMem0LongTermMemory.created[0]["on_disk"] is False
    assert DummyMem0LongTermMemory.created[0]["model"]["chat"]["model_name"] == "qwen3.7-max"
    vector_store_config = DummyMem0LongTermMemory.created[0]["vector_store_config"]
    assert vector_store_config.provider == "milvus"
    assert vector_store_config.config.url == "http://localhost:19531"
    assert vector_store_config.config.collection_name == "voice_calendar_memories"
    assert vector_store_config.config.embedding_model_dims == 1024
    assert vector_store_config.config.metric_type == "COSINE"


@pytest.mark.asyncio
async def test_long_term_memory_record_times_out(monkeypatch):
    monkeypatch.setattr(memory_module.settings, "memory_long_term_timeout_seconds", 1)

    class SlowLongTermMemory:
        async def record(self, msgs, **kwargs):
            await asyncio.sleep(2)
            return {"ok": True}

    memory = VoiceCalendarLongTermMemory(SlowLongTermMemory(), "user_timeout")

    result = await memory.record([])

    assert result == {}
