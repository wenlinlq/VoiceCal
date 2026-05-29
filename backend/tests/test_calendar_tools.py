from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.tools.calendar_tools import (
    TOOL_DEFINITIONS,
    TOOL_REGISTRY,
    add_calendar_event_tool,
    check_time_conflict_tool,
    delete_calendar_event_tool,
    detect_duplicate_events_tool,
    parse_datetime_tool,
    query_calendar_events_tool,
    suggest_available_slots_tool,
    update_calendar_event_tool,
    _to_iso,
)


@pytest.fixture
def future_event_args():
    start_time = datetime.now(timezone.utc) + timedelta(days=1, hours=1)
    end_time = start_time + timedelta(hours=1)
    return {
        "title": "项目会议",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "confirm": True,  # 工具直调测试跳过用户确认
    }


@pytest.mark.asyncio
async def test_parse_datetime_complete(db_session):
    result = await parse_datetime_tool(
        db_session,
        "demo_user",
        {
            "text": "明天下午三点",
            "current_time": "2026-05-29T15:30:00+08:00",
            "timezone": "Asia/Shanghai",
        },
    )
    assert result["success"] is True
    assert result["data"]["is_complete"] is True
    assert result["data"]["start_time"].startswith("2026-05-30T15:00:00")


@pytest.mark.asyncio
async def test_parse_datetime_missing_time(db_session):
    result = await parse_datetime_tool(
        db_session,
        "demo_user",
        {
            "text": "明天开会",
            "current_time": "2026-05-29T15:30:00+08:00",
            "timezone": "Asia/Shanghai",
        },
    )
    assert result["success"] is True
    assert result["data"]["is_complete"] is False
    assert "具体时间" in result["data"]["missing_fields"]


@pytest.mark.asyncio
async def test_add_event_and_query_structured(db_session, future_event_args):
    created = await add_calendar_event_tool(db_session, "demo_user", future_event_args)
    assert created["success"] is True
    assert created["data"]["event"]["title"] == "项目会议"
    assert created["error_code"] is None

    queried = await query_calendar_events_tool(db_session, "demo_user", {})
    assert queried["success"] is True
    assert queried["data"]["count"] == 1


@pytest.mark.asyncio
async def test_add_event_detects_conflict(db_session, future_event_args):
    await add_calendar_event_tool(db_session, "demo_user", future_event_args)
    result = await add_calendar_event_tool(
        db_session,
        "demo_user",
        {**future_event_args, "title": "导师沟通"},
    )
    assert result["success"] is False
    assert result["error_code"] == "TIME_CONFLICT"
    assert result["data"]["conflicts"]


@pytest.mark.asyncio
async def test_force_add_allows_conflict(db_session, future_event_args):
    await add_calendar_event_tool(db_session, "demo_user", future_event_args)
    result = await add_calendar_event_tool(
        db_session,
        "demo_user",
        {**future_event_args, "title": "导师沟通", "force": True},
    )
    assert result["success"] is True


@pytest.mark.asyncio
async def test_duplicate_detection(db_session, future_event_args):
    await add_calendar_event_tool(db_session, "demo_user", future_event_args)
    result = await detect_duplicate_events_tool(db_session, "demo_user", future_event_args)
    assert result["success"] is True
    assert result["data"]["has_duplicate"] is True


@pytest.mark.asyncio
async def test_check_time_conflict(db_session, future_event_args):
    await add_calendar_event_tool(db_session, "demo_user", future_event_args)
    result = await check_time_conflict_tool(db_session, "demo_user", future_event_args)
    assert result["success"] is True
    assert result["data"]["has_conflict"] is True


@pytest.mark.asyncio
async def test_suggest_available_slots(db_session, future_event_args):
    result = await suggest_available_slots_tool(db_session, "demo_user", future_event_args)
    assert result["success"] is True
    assert "suggestions" in result["data"]


@pytest.mark.asyncio
async def test_delete_requires_event_id(db_session):
    result = await delete_calendar_event_tool(db_session, "demo_user", {})
    assert result["success"] is False
    assert result["error_code"] == "EVENT_NOT_FOUND"


# ---------- 确认流程测试 ----------

@pytest.mark.asyncio
async def test_add_event_requires_confirm(db_session, future_event_args):
    """不带 confirm 时返回 CONFIRM_REQUIRED + preview，不实际创建"""
    args = {k: v for k, v in future_event_args.items() if k != "confirm"}
    result = await add_calendar_event_tool(db_session, "demo_user", args)
    assert result["success"] is False
    assert result["error_code"] == "CONFIRM_REQUIRED"
    assert result["data"]["preview"]["title"] == "项目会议"

    # 确认没有实际创建
    query_result = await query_calendar_events_tool(db_session, "demo_user", {})
    assert query_result["data"]["count"] == 0


@pytest.mark.asyncio
async def test_add_event_with_confirm_succeeds(db_session, future_event_args):
    """带 confirm=True 时正常创建"""
    result = await add_calendar_event_tool(db_session, "demo_user", future_event_args)
    assert result["success"] is True
    assert result["error_code"] is None
    assert result["data"]["event"]["title"] == "项目会议"


@pytest.mark.asyncio
async def test_delete_event_requires_confirm(db_session, future_event_args):
    """删除也需要确认"""
    created = await add_calendar_event_tool(db_session, "demo_user", future_event_args)
    event_id = created["data"]["event"]["event_id"]

    # 不带 confirm → CONFIRM_REQUIRED
    result = await delete_calendar_event_tool(db_session, "demo_user", {"event_id": event_id})
    assert result["success"] is False
    assert result["error_code"] == "CONFIRM_REQUIRED"
    assert result["data"]["preview"]["title"] == "项目会议"

    # 确认未删除
    query_result = await query_calendar_events_tool(db_session, "demo_user", {})
    assert query_result["data"]["count"] == 1

    # 带 confirm → 真正删除
    result2 = await delete_calendar_event_tool(db_session, "demo_user", {"event_id": event_id, "confirm": True})
    assert result2["success"] is True

    query_result2 = await query_calendar_events_tool(db_session, "demo_user", {})
    assert query_result2["data"]["count"] == 0


@pytest.mark.asyncio
async def test_update_event_requires_confirm(db_session):
    """修改也需要确认"""
    start_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    end_time = (datetime.now(timezone.utc) + timedelta(days=1, hours=1)).isoformat()
    created = await add_calendar_event_tool(
        db_session, "demo_user",
        {"title": "原日程", "start_time": start_time, "end_time": end_time, "confirm": True},
    )
    event_id = created["data"]["event"]["event_id"]

    # 不带 confirm → CONFIRM_REQUIRED + changes
    result = await update_calendar_event_tool(
        db_session, "demo_user",
        {"event_id": event_id, "title": "新标题", "confirm": False},
    )
    assert result["success"] is False
    assert result["error_code"] == "CONFIRM_REQUIRED"
    assert result["data"]["changes"]["title"] == "新标题"

    # 带 confirm → 真正修改
    result2 = await update_calendar_event_tool(
        db_session, "demo_user",
        {"event_id": event_id, "title": "新标题", "confirm": True},
    )
    assert result2["success"] is True
    assert result2["data"]["event"]["title"] == "新标题"


@pytest.mark.asyncio
async def test_confirm_after_conflict_still_returns_conflict(db_session, future_event_args):
    """确认检查在冲突检查之后，有冲突时优先返回冲突"""
    await add_calendar_event_tool(db_session, "demo_user", future_event_args)
    # 不带 confirm 的冲突请求
    args = {k: v for k, v in future_event_args.items() if k != "confirm"}
    args["title"] = "另一件事"
    result = await add_calendar_event_tool(db_session, "demo_user", args)
    assert result["error_code"] == "TIME_CONFLICT"  # 冲突优先，不是 CONFIRM_REQUIRED


@pytest.mark.asyncio
async def test_query_by_keyword(db_session):
    """关键词搜索：按标题和描述模糊匹配"""
    from app.tools.calendar_tools import add_calendar_event_tool
    from datetime import datetime, timedelta, timezone

    t = datetime.now(timezone.utc) + timedelta(days=1)
    await add_calendar_event_tool(db_session, "demo_user", {
        "title": "七牛云面试",
        "start_time": (t + timedelta(hours=14)).isoformat(),
        "end_time": (t + timedelta(hours=15)).isoformat(),
        "confirm": True,
    })
    await add_calendar_event_tool(db_session, "demo_user", {
        "title": "项目会议",
        "description": "讨论七牛云方案",
        "start_time": (t + timedelta(hours=16)).isoformat(),
        "end_time": (t + timedelta(hours=17)).isoformat(),
        "confirm": True,
    })
    await add_calendar_event_tool(db_session, "demo_user", {
        "title": "健身",
        "start_time": (t + timedelta(hours=18)).isoformat(),
        "end_time": (t + timedelta(hours=19)).isoformat(),
        "confirm": True,
    })

    # 关键词"七牛云"应匹配标题和描述
    result = await query_calendar_events_tool(db_session, "demo_user", {"keyword": "七牛云"})
    assert result["data"]["count"] == 2
    titles = [e["title"] for e in result["data"]["events"]]
    assert "七牛云面试" in titles
    assert "项目会议" in titles

    # 关键词"健身"只匹配一个
    result2 = await query_calendar_events_tool(db_session, "demo_user", {"keyword": "健身"})
    assert result2["data"]["count"] == 1

    # 不存在的关键词
    result3 = await query_calendar_events_tool(db_session, "demo_user", {"keyword": "不存在"})
    assert result3["data"]["count"] == 0


@pytest.mark.asyncio
async def test_get_event_by_id(db_session):
    """按 ID 查询单个日程"""
    from app.tools.calendar_tools import add_calendar_event_tool, get_event_by_id_impl
    from datetime import datetime, timedelta, timezone

    t = datetime.now(timezone.utc) + timedelta(days=1)
    created = await add_calendar_event_tool(db_session, "demo_user", {
        "title": "测试日程",
        "start_time": (t + timedelta(hours=10)).isoformat(),
        "end_time": (t + timedelta(hours=11)).isoformat(),
        "confirm": True,
    })
    event_id = created["data"]["event"]["event_id"]

    result = await get_event_by_id_impl(db_session, "demo_user", {"event_id": event_id})
    assert result["success"] is True
    assert result["data"]["event"]["title"] == "测试日程"

    # 不存在的 ID
    fake = await get_event_by_id_impl(db_session, "demo_user", {"event_id": "00000000-0000-0000-0000-000000000000"})
    assert fake["success"] is False
    assert fake["error_code"] == "EVENT_NOT_FOUND"


def test_tool_registry():
    expected = {
        "get_current_time",
        "parse_datetime",
        "query_calendar_events",
        "check_time_conflict",
        "detect_duplicate_events",
        "suggest_available_slots",
        "add_calendar_event",
        "delete_calendar_event",
        "update_calendar_event",
        "create_reminder",
        "get_event_by_id",
    }
    assert set(TOOL_REGISTRY.keys()) == expected
    assert len(TOOL_DEFINITIONS) == 11


def test_to_iso_normalizes_utc_to_default_timezone():
    value = datetime(2026, 5, 30, 7, 0, tzinfo=timezone.utc)
    assert _to_iso(value) == "2026-05-30T15:00:00+08:00"


@pytest.mark.asyncio
async def test_check_time_conflict_handles_timezone_aware_events(db_session, monkeypatch):
    fake_event = SimpleNamespace(
        id="evt_001",
        title="组会",
        description=None,
        location=None,
        start_time=datetime(2026, 5, 30, 7, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 5, 30, 8, 0, tzinfo=timezone.utc),
        is_all_day=False,
    )

    async def fake_load_user_events(db, user_id):
        return [fake_event]

    monkeypatch.setattr("app.tools.calendar_tools._load_user_events", fake_load_user_events)

    result = await check_time_conflict_tool(
        db_session,
        "demo_user",
        {
            "start_time": "2026-05-30T15:00:00+08:00",
            "end_time": "2026-05-30T16:00:00+08:00",
        },
    )
    assert result["success"] is True
    assert result["data"]["has_conflict"] is True
