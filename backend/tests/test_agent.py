import base64
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.agent_service import CalendarAgentService
from app.services.calendar_service import CalendarService


def _make_mock_result(reply_text="好的，已为你添加日程。"):
    mock_result = MagicMock()
    mock_result.content = [MagicMock()]
    mock_result.content[0].text = reply_text
    mock_result.get_text_content.return_value = reply_text
    return mock_result


@pytest.mark.asyncio
async def test_service_fallback_requires_confirm_on_create(db_session):
    """兜底路径不带 skip_confirm 时，返回 CONFIRM_REQUIRED，不落库"""
    svc = CalendarAgentService()

    with patch("app.services.agent_service.ReActAgent") as mock_agent_cls:
        mock_agent = AsyncMock(return_value=_make_mock_result("好的，已为你添加日程。"))
        mock_agent_cls.return_value = mock_agent

        result = await svc.handle_text(db_session, "test_openid_agent", "明天下午三点提醒我开组会")

    # 安全网纠正了 agent 的完成语 → 确认提问
    assert "确认" in result["reply_text"]
    assert "组会" in result["reply_text"]
    assert result["need_confirm"] is True
    assert result["speech"] is None

    # 还没落库
    events = await CalendarService(db_session, "test_openid_agent").query_events()
    assert len(events) == 0


@pytest.mark.asyncio
async def test_service_fallback_with_confirm_creates_event(db_session):
    """用户说"确认"后，skip_confirm=True，兜底落库成功"""
    svc = CalendarAgentService()

    with patch("app.services.agent_service.ReActAgent") as mock_agent_cls:
        mock_agent = AsyncMock(return_value=_make_mock_result("好的。"))
        mock_agent_cls.return_value = mock_agent

        result = await svc.handle_text(db_session, "test_openid_agent", "确认")

    # "确认" 不包含时间和创建关键词，兜底不执行，直接透传 agent 回复
    assert result["need_confirm"] is False
    assert result["reply_text"] == "好的。"


@pytest.mark.asyncio
async def test_service_speech_fallback(db_session):
    svc = CalendarAgentService()

    with patch("app.services.agent_service.ReActAgent") as mock_agent_cls:
        mock_agent = AsyncMock(return_value=_make_mock_result("查询结果：没有日程。"))
        mock_agent_cls.return_value = mock_agent

        result = await svc.handle_text(db_session, "test_openid_agent", "今天有什么安排")
        assert result["reply_text"] == "查询结果：没有日程。"


@pytest.mark.asyncio
async def test_need_confirm_true_on_time_conflict(db_session):
    """时间冲突时 need_confirm=True"""
    svc = CalendarAgentService()

    with patch("app.services.agent_service.ReActAgent") as mock_agent_cls:
        mock_agent = AsyncMock(return_value=_make_mock_result("好的。"))
        mock_agent_cls.return_value = mock_agent

        # 直接通过工具创建一个事件（模拟"用户已确认"后的落库）
        from app.tools.calendar_tools import TOOL_REGISTRY
        from datetime import datetime, timedelta, timezone

        start_time = datetime.now(timezone.utc) + timedelta(days=1, hours=1)
        end_time = start_time + timedelta(hours=1)
        await TOOL_REGISTRY["add_calendar_event"](
            db_session, "test_openid_agent",
            {
                "title": "项目会议",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "confirm": True,
            },
        )

        # 再用相同时间创建 → 兜底触发 TIME_CONFLICT → need_confirm=True
        second = await svc.handle_text(
            db_session, "test_openid_agent",
            f"明天下午三点安排项目会议",
        )
        assert second["need_confirm"] is True


@pytest.mark.asyncio
async def test_progress_reply_replaced_by_tool_confirmation(db_session):
    """Agent 只输出“正在…”时，用工具结果兜底为确认提问"""
    svc = CalendarAgentService()

    time_conflict = {
        "success": False,
        "message": "该时间段存在冲突日程",
        "error_code": "TIME_CONFLICT",
        "data": {"conflicts": [{"title": "组会"}]},
    }

    def _fake_create_toolkit(db, user_id, tool_calls):
        tool_calls.append({"name": "create_reminder", "result": time_conflict})
        return MagicMock()

    with patch.object(svc, "_create_toolkit", side_effect=_fake_create_toolkit), patch(
        "app.services.agent_service.ReActAgent"
    ) as mock_agent_cls:
        mock_agent = AsyncMock(return_value=_make_mock_result("正在查询你近期的日程安排……"))
        mock_agent_cls.return_value = mock_agent

        result = await svc.handle_text(db_session, "test_openid_agent", "明天下午三点提醒我开组会。")
        assert "还要继续添加吗" in result["reply_text"]
        assert result["need_confirm"] is True


@pytest.mark.asyncio
async def test_streaming_speech_only_forwards_incremental_audio(db_session):
    svc = CalendarAgentService()
    chunk1 = b"\x01\x02" * 16
    chunk2 = b"\x03\x04" * 8
    chunk1_b64 = base64.b64encode(chunk1).decode()
    chunk2_b64 = base64.b64encode(chunk2).decode()

    class FakeSpeechAgent:
        def register_instance_hook(self, hook_type, hook_name, hook):
            self.post_print_hook = hook

        async def __call__(self, user_msg):
            msg = SimpleNamespace(id="msg-stream-1")
            await self.post_print_hook(
                self,
                {
                    "msg": msg,
                    "last": False,
                    "speech": {"source": {"type": "base64", "data": chunk1_b64}},
                },
                None,
            )
            await self.post_print_hook(
                self,
                {
                    "msg": msg,
                    "last": True,
                    "speech": {"source": {"type": "base64", "data": chunk1_b64 + chunk2_b64}},
                },
                None,
            )
            return _make_mock_result("你好")

    streamed = []

    async def on_speech_chunk(chunk: bytes, is_last: bool):
        streamed.append((chunk, is_last))

    with patch("app.services.agent_service.ReActAgent", return_value=FakeSpeechAgent()):
        result = await svc.handle_text(
            db_session,
            "test_openid_agent",
            "你好",
            on_speech_chunk=on_speech_chunk,
        )

    assert result["speech_streamed"] is True
    assert result["speech"] is None
    assert streamed == [
        (chunk1, False),
        (chunk2, True),
    ]


@pytest.mark.asyncio
async def test_streaming_speech_emits_empty_last_marker_when_final_print_has_no_new_audio(db_session):
    svc = CalendarAgentService()
    chunk1 = b"\x01\x02" * 16
    chunk1_b64 = base64.b64encode(chunk1).decode()

    class FakeSpeechAgent:
        def register_instance_hook(self, hook_type, hook_name, hook):
            self.post_print_hook = hook

        async def __call__(self, user_msg):
            msg = SimpleNamespace(id="msg-stream-2")
            await self.post_print_hook(
                self,
                {
                    "msg": msg,
                    "last": False,
                    "speech": {"source": {"type": "base64", "data": chunk1_b64}},
                },
                None,
            )
            await self.post_print_hook(
                self,
                {
                    "msg": msg,
                    "last": True,
                    "speech": {"source": {"type": "base64", "data": chunk1_b64}},
                },
                None,
            )
            return _make_mock_result("你好")

    streamed = []

    async def on_speech_chunk(chunk: bytes, is_last: bool):
        streamed.append((chunk, is_last))

    with patch("app.services.agent_service.ReActAgent", return_value=FakeSpeechAgent()):
        result = await svc.handle_text(
            db_session,
            "test_openid_agent",
            "你好",
            on_speech_chunk=on_speech_chunk,
        )

    assert result["speech_streamed"] is True
    assert result["speech"] is None
    assert streamed == [
        (chunk1, False),
        (b"", True),
    ]
