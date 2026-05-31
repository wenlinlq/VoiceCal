"""
日历工具层。

核心实现接收 db/user_id/args，便于单元测试和服务层调用；
AgentScope 注册时使用无内部依赖的包装器，只暴露 JSON 结构参数。
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, time, timedelta, timezone
from typing import Any, Callable, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.event_schema import EventCreate, EventUpdate
from app.services.calendar_service import CalendarService

logger = logging.getLogger(__name__)

DEFAULT_TIMEZONE = timezone(timedelta(hours=8))


def _ok(data: Any = None, message: str = "操作成功") -> dict[str, Any]:
    return {"success": True, "data": data, "message": message, "error_code": None}


def _fail(message: str, error_code: str, data: Any = None) -> dict[str, Any]:
    return {"success": False, "data": data, "message": message, "error_code": error_code}


def _parse_iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=DEFAULT_TIMEZONE)
    return parsed


def _to_iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return _as_aware(value).isoformat()


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value or "").lower()


def _as_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=DEFAULT_TIMEZONE)
    return value.astimezone(DEFAULT_TIMEZONE)


def _same_day_window(anchor: datetime) -> tuple[datetime, datetime]:
    start = anchor.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end


def _build_event_data(event) -> dict[str, Any]:
    return {
        "event_id": str(event.id),
        "id": str(event.id),
        "title": event.title,
        "description": event.description,
        "location": event.location,
        "start_time": _to_iso(event.start_time),
        "end_time": _to_iso(event.end_time),
        "is_all_day": event.is_all_day,
        "completed": getattr(event, "completed", False),
    }


async def _load_user_events(db: AsyncSession, user_id: str) -> list[Any]:
    service = CalendarService(db, user_id)
    return await service.query_events()


def _extract_slots(text: str) -> tuple[Optional[int], Optional[int], Optional[str], list[str]]:
    lowered = text.replace(" ", "")
    missing_fields: list[str] = []
    hour = None
    minute = 0

    chinese_digits = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    time_match = re.search(r"(\d{1,2}|[一二两三四五六七八九十])点((\d{1,2})分?)?", lowered)
    if time_match:
        hour_text = time_match.group(1)
        hour = int(hour_text) if hour_text.isdigit() else chinese_digits[hour_text]
        minute = int(time_match.group(3) or 0)
        if "下午" in lowered or "晚上" in lowered or "傍晚" in lowered:
            if hour < 12:
                hour += 12
        if "上午" in lowered and hour == 12:
            hour = 0
    else:
        missing_fields.append("具体时间")

    day_hint = None
    if "明天" in lowered:
        day_hint = "tomorrow"
    elif "后天" in lowered:
        day_hint = "day_after_tomorrow"
    elif "今天" in lowered:
        day_hint = "today"
    elif "下周" in lowered:
        day_hint = "next_week"
    elif "本周" in lowered:
        day_hint = "this_week"
    elif "半小时后" in lowered:
        day_hint = "in_30_min"
    elif "十分钟后" in lowered:
        day_hint = "in_10_min"
    elif "两天后" in lowered:
        day_hint = "in_2_days"

    return hour, minute, day_hint, missing_fields


def _extract_reference_date(current_time: datetime, text: str) -> tuple[datetime, list[str]]:
    """从文本中提取参考日期，支持多种中文表达。"""
    lowered = text.replace(" ", "")
    missing_fields: list[str] = []
    weekday_map = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6, "1": 0, "2": 1, "3": 2, "4": 3, "5": 4, "6": 5, "7": 6}

    # ── 相对日期 ──
    if "大后天" in lowered:
        return current_time + timedelta(days=3), missing_fields
    if "后天" in lowered:
        return current_time + timedelta(days=2), missing_fields
    if "明天" in lowered:
        return current_time + timedelta(days=1), missing_fields
    if "今天" in lowered:
        return current_time, missing_fields
    if "大前天" in lowered:
        return current_time - timedelta(days=3), missing_fields
    if "前天" in lowered:
        return current_time - timedelta(days=2), missing_fields
    if "昨天" in lowered:
        return current_time - timedelta(days=1), missing_fields

    # "X天后" / "X天之后"
    days_after = re.search(r"(\d+)天[之以]?后", lowered)
    if days_after:
        return current_time + timedelta(days=int(days_after.group(1))), missing_fields

    # "X小时后" / "X小时之后"
    hours_after = re.search(r"(\d+)小时[之以]?后", lowered)
    if hours_after:
        return current_time + timedelta(hours=int(hours_after.group(1))), missing_fields

    # "X分钟后" / "X分钟之后"
    mins_after = re.search(r"(\d+)分钟[之以]?后", lowered)
    if mins_after:
        return current_time + timedelta(minutes=int(mins_after.group(1))), missing_fields

    # "半小时后" / "半小时之后"
    if "半小时" in lowered and "后" in lowered:
        return current_time + timedelta(minutes=30), missing_fields
    if "半小时后" in lowered:
        return current_time + timedelta(minutes=30), missing_fields

    # ── 星期 ──
    # "下周一" / "下星期3" / "下周2"
    next_week = re.search(r"下周([一二三四五六日天\d])", lowered)
    if next_week:
        wd = weekday_map[next_week.group(1)]
        start_of_week = current_time - timedelta(days=current_time.weekday())
        return start_of_week + timedelta(days=7 + wd), missing_fields

    # "下周一" 的变体: "下星期一" / "下个星期一"
    next_week2 = re.search(r"下(?:个)?(?:星期|礼拜)([一二三四五六日天\d])", lowered)
    if next_week2:
        wd = weekday_map[next_week2.group(1)]
        start_of_week = current_time - timedelta(days=current_time.weekday())
        return start_of_week + timedelta(days=7 + wd), missing_fields

    # "本周一" / "这周一"
    this_week = re.search(r"[本这]周([一二三四五六日天\d])", lowered)
    if this_week:
        wd = weekday_map[this_week.group(1)]
        start_of_week = current_time - timedelta(days=current_time.weekday())
        return start_of_week + timedelta(days=wd), missing_fields

    # "周一" / "星期二"（没有周前缀，默认最近的那个）
    plain_weekday = re.search(r"(?:星期|礼拜)([一二三四五六日天\d])", lowered)
    if plain_weekday:
        wd = weekday_map[plain_weekday.group(1)]
        days_ahead = wd - current_time.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return current_time + timedelta(days=days_ahead), missing_fields

    # "下下周" → 下周再往后推7天
    # （简单兼容，只匹配 "下下周" 模式）
    if "下下周" in lowered:
        # 算下周的日期再 +7
        start_of_week = current_time - timedelta(days=current_time.weekday())
        return start_of_week + timedelta(days=14 + current_time.weekday()), missing_fields

    # ── 绝对日期 ──
    # "6月2号" / "12月31日" / "6月2"
    month_day = re.search(r"(\d{1,2})月(\d{1,2})[号日]?", lowered)
    if month_day:
        month = int(month_day.group(1))
        day = int(month_day.group(2))
        try:
            ref = current_time.replace(month=month, day=day, hour=0, minute=0, second=0, microsecond=0)
            return ref, missing_fields
        except ValueError:
            pass

    # 纯数字日: "2号" / "15日"（不含月，默认当前月）
    day_only = re.search(r"(?<!\d)(\d{1,2})[号日](?![\d年月])", lowered)
    if day_only:
        day = int(day_only.group(1))
        try:
            ref = current_time.replace(day=day, hour=0, minute=0, second=0, microsecond=0)
            if ref < current_time:
                if current_time.month == 12:
                    ref = ref.replace(year=current_time.year + 1, month=1)
                else:
                    ref = ref.replace(month=current_time.month + 1)
            return ref, missing_fields
        except ValueError:
            pass

    # ISO 日期: "2026-06-02"
    iso_date = re.search(r"(\d{4})-(\d{2})-(\d{2})", lowered)
    if iso_date:
        try:
            y, m, d = int(iso_date.group(1)), int(iso_date.group(2)), int(iso_date.group(3))
            return current_time.replace(year=y, month=m, day=d, hour=0, minute=0, second=0, microsecond=0), missing_fields
        except ValueError:
            pass

    # "工作日" → 返回当前日期（非周末）
    if "工作日" in lowered:
        return current_time, missing_fields

    missing_fields.append("具体日期")
    return current_time, missing_fields


async def get_current_time_impl(db: AsyncSession, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(DEFAULT_TIMEZONE)
    return _ok({"current_time": now.isoformat(), "timezone": "Asia/Shanghai"})


async def parse_datetime_impl(db: AsyncSession, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    text = (args.get("text") or "").strip()
    current_time_raw = args.get("current_time")
    timezone_name = args.get("timezone") or "Asia/Shanghai"
    logger.info("[工具][parse_datetime] 输入 text=%s current_time=%s timezone=%s", text, current_time_raw, timezone_name)

    if not text:
        return _fail("缺少时间文本", "INVALID_TIME")

    current_time = _parse_iso_datetime(current_time_raw) if current_time_raw else datetime.now(DEFAULT_TIMEZONE)
    reference_date, missing_fields = _extract_reference_date(current_time, text)
    hour, minute, _, extra_missing = _extract_slots(text)
    missing_fields.extend(extra_missing)

    start_time = None
    end_time = None
    day_specific = any(keyword in text for keyword in ("今天", "明天", "后天", "下周", "本周", "半小时后", "十分钟后", "两天后"))
    if hour is not None:
        target_date = reference_date.date()
        start_time = datetime.combine(target_date, time(hour=hour, minute=minute), tzinfo=current_time.tzinfo or DEFAULT_TIMEZONE)
        end_time = start_time + timedelta(minutes=int(args.get("duration_minutes") or 60))
    else:
        if not missing_fields:
            missing_fields.append("具体时间")

    if day_specific and "具体日期" in missing_fields:
        missing_fields.remove("具体日期")

    is_complete = not missing_fields and start_time is not None and end_time is not None
    question = ""
    if missing_fields:
        question = "请问" + "、".join(sorted(set(missing_fields))) + "？"

    confidence = 0.95 if is_complete else 0.45
    if "每周" in text or "每月" in text or "工作日" in text:
        confidence = min(confidence, 0.6)

    return _ok(
        {
            "success": True,
            "start_time": _to_iso(start_time),
            "end_time": _to_iso(end_time),
            "is_complete": is_complete,
            "missing_fields": sorted(set(missing_fields)),
            "question": question,
            "confidence": confidence,
            "timezone": timezone_name,
            "current_time": current_time.isoformat(),
        }
    )


async def query_calendar_events_impl(db: AsyncSession, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    logger.info("[工具][query_calendar_events] 输入=%s", args)
    service = CalendarService(db, user_id)
    start_time = _as_aware(_parse_iso_datetime(args["start_time"])) if args.get("start_time") else None
    end_time = _as_aware(_parse_iso_datetime(args["end_time"])) if args.get("end_time") else None
    keyword = args.get("keyword")
    events = await service.query_events(start_time=start_time, end_time=end_time, keyword=keyword)
    return _ok({"events": [_build_event_data(event) for event in events], "count": len(events)})


async def check_time_conflict_impl(db: AsyncSession, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    logger.info("[工具][check_time_conflict] 输入=%s", args)
    start_time = _as_aware(_parse_iso_datetime(args["start_time"]))
    end_time = _as_aware(_parse_iso_datetime(args["end_time"]))
    events = await _load_user_events(db, user_id)
    conflicts = []
    for event in events:
        event_start = _as_aware(event.start_time)
        event_end = _as_aware(event.end_time)
        if not (event_end <= start_time or event_start >= end_time):
            conflicts.append(_build_event_data(event))
    return _ok({"has_conflict": bool(conflicts), "conflicts": conflicts})


async def detect_duplicate_events_impl(db: AsyncSession, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    logger.info("[工具][detect_duplicate_events] 输入=%s", args)
    title = _normalize_text(args.get("title", ""))
    start_time = _as_aware(_parse_iso_datetime(args["start_time"]))
    events = await _load_user_events(db, user_id)
    duplicates = []
    for event in events:
        event_start = _as_aware(event.start_time)
        if _normalize_text(event.title) == title and abs((event_start - start_time).total_seconds()) < 300:
            duplicates.append(_build_event_data(event))
    return _ok({"has_duplicate": bool(duplicates), "duplicates": duplicates, "message": "发现相似日程" if duplicates else "未发现重复日程"})


async def suggest_available_slots_impl(db: AsyncSession, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    logger.info("[工具][suggest_available_slots] 输入=%s", args)
    start_time = _as_aware(_parse_iso_datetime(args["start_time"]))
    end_time = _as_aware(_parse_iso_datetime(args["end_time"]))
    duration_minutes = int(args.get("duration_minutes") or max(30, int((end_time - start_time).total_seconds() // 60)))
    events = await _load_user_events(db, user_id)
    day_start, day_end = _same_day_window(start_time)
    busy = sorted(events, key=lambda event: _as_aware(event.start_time))
    cursor = day_start
    slots: list[dict[str, Any]] = []
    for event in busy:
        event_start = _as_aware(event.start_time)
        event_end = _as_aware(event.end_time)
        if cursor + timedelta(minutes=duration_minutes) <= event_start:
            candidate_end = cursor + timedelta(minutes=duration_minutes)
            slots.append({"start_time": _to_iso(cursor), "end_time": _to_iso(candidate_end), "reason": "前方可用"})
        cursor = max(cursor, event_end)
    if cursor + timedelta(minutes=duration_minutes) <= day_end:
        candidate_end = cursor + timedelta(minutes=duration_minutes)
        slots.append({"start_time": _to_iso(cursor), "end_time": _to_iso(candidate_end), "reason": "当天尾部可用"})
    return _ok({"suggestions": slots[:5]})


async def add_calendar_event_impl(db: AsyncSession, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    logger.info("[工具][add_calendar_event] 输入=%s", args)
    title = (args.get("title") or "").strip()
    start_time = _as_aware(_parse_iso_datetime(args["start_time"]))
    end_time = _as_aware(_parse_iso_datetime(args["end_time"]))
    force = bool(args.get("force", False))

    if not title:
        return _fail("缺少日程标题", "INVALID_TIME")
    if end_time <= start_time:
        return _fail("结束时间必须晚于开始时间", "INVALID_TIME")
    if start_time < datetime.now(start_time.tzinfo or DEFAULT_TIMEZONE) and not args.get("allow_past", False):
        return _fail("不能创建明显已经过去的日程", "PAST_TIME")

    conflict_result = await check_time_conflict_impl(db, user_id, args)
    conflicts = conflict_result["data"]["conflicts"] if conflict_result["success"] else []
    if conflicts and not force:
        suggestions = await suggest_available_slots_impl(
            db,
            user_id,
            {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_minutes": int((end_time - start_time).total_seconds() // 60),
            },
        )
        return _fail("该时间段存在冲突日程", "TIME_CONFLICT", {"conflicts": conflicts, "suggestions": suggestions["data"]["suggestions"] if suggestions["success"] else []})

    duplicate_result = await detect_duplicate_events_impl(db, user_id, args)
    duplicates = duplicate_result["data"]["duplicates"] if duplicate_result["success"] else []
    if duplicates and not force:
        return _fail("发现疑似重复日程", "DUPLICATE_EVENT", {"duplicates": duplicates})

    # 用户确认检查：首次调用不带 confirm 时返回预览，用户确认后带 confirm=True 重试
    if not args.get("confirm", False):
        return _fail("请确认是否创建此日程", "CONFIRM_REQUIRED", {
            "preview": {
                "title": title,
                "start_time": _to_iso(start_time),
                "end_time": _to_iso(end_time),
                "location": args.get("location"),
                "description": args.get("description"),
            }
        })

    service = CalendarService(db, user_id)
    event = await service.create_event(
        EventCreate(
            title=title,
            description=args.get("description"),
            location=args.get("location"),
            start_time=start_time,
            end_time=end_time,
            is_all_day=bool(args.get("is_all_day", False)),
            completed=bool(args.get("completed", False)),
        )
    )
    return _ok({"event": _build_event_data(event)}, "日程已创建")


async def delete_calendar_event_impl(db: AsyncSession, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    logger.info("[工具][delete_calendar_event] 输入=%s", args)
    event_id = args.get("event_id")
    if not event_id:
        return _fail("缺少 event_id", "EVENT_NOT_FOUND")
    service = CalendarService(db, user_id)
    try:
        existing = await service.get_event(uuid.UUID(event_id))
    except (ValueError, TypeError):
        existing = None
    if not existing:
        return _fail("未找到可删除日程", "EVENT_NOT_FOUND")

    if not args.get("confirm", False):
        return _fail("请确认是否删除此日程", "CONFIRM_REQUIRED", {
            "preview": {
                "event_id": str(existing.id),
                "title": existing.title,
                "start_time": _to_iso(existing.start_time),
                "end_time": _to_iso(existing.end_time),
            }
        })

    deleted = await service.delete_event(uuid.UUID(event_id))
    if not deleted:
        return _fail("未找到可删除日程", "EVENT_NOT_FOUND")
    return _ok({"event_id": event_id}, "日程已删除")


async def update_calendar_event_impl(db: AsyncSession, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    logger.info("[工具][update_calendar_event] 输入=%s", args)
    event_id = args.get("event_id")
    if not event_id:
        return _fail("缺少 event_id", "EVENT_NOT_FOUND")
    service = CalendarService(db, user_id)
    existing = await service.get_event(uuid.UUID(event_id))
    if not existing:
        return _fail("未找到可修改日程", "EVENT_NOT_FOUND")

    if not args.get("confirm", False):
        preview = {
            "event_id": str(existing.id),
            "title": existing.title,
            "start_time": _to_iso(existing.start_time),
            "end_time": _to_iso(existing.end_time),
        }
        changes = {}
        if "title" in args:
            changes["title"] = args["title"]
        if "start_time" in args:
            changes["start_time"] = args["start_time"]
        if "end_time" in args:
            changes["end_time"] = args["end_time"]
        if "location" in args:
            changes["location"] = args["location"]
        if "description" in args:
            changes["description"] = args["description"]
        if "completed" in args:
            changes["completed"] = args["completed"]
        return _fail("请确认是否修改此日程", "CONFIRM_REQUIRED", {"preview": preview, "changes": changes})

    update = EventUpdate()
    if "title" in args:
        update.title = args["title"]
    if "description" in args:
        update.description = args["description"]
    if "location" in args:
        update.location = args["location"]
    if "start_time" in args:
        update.start_time = _as_aware(_parse_iso_datetime(args["start_time"]))
    if "end_time" in args:
        update.end_time = _as_aware(_parse_iso_datetime(args["end_time"]))
    if "is_all_day" in args:
        update.is_all_day = args["is_all_day"]
    if "completed" in args:
        update.completed = args["completed"]

    event = await service.update_event(uuid.UUID(event_id), update)
    if not event:
        return _fail("未找到可修改日程", "EVENT_NOT_FOUND")
    return _ok(
        {
            "event": {
                "event_id": str(event.id),
                "title": event.title,
                "old_start_time": _to_iso(existing.start_time),
                "new_start_time": _to_iso(event.start_time),
            }
        },
        "日程修改成功",
    )


async def create_reminder_impl(db: AsyncSession, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    reminder_args = dict(args)
    reminder_args.setdefault("title", args.get("title") or "提醒")
    result = await add_calendar_event_impl(db, user_id, reminder_args)
    if result["success"]:
        result["data"]["reminder"] = True
    return result


async def get_event_by_id_impl(db: AsyncSession, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    logger.info("[工具][get_event_by_id] 输入=%s", args)
    event_id = args.get("event_id")
    if not event_id:
        return _fail("缺少 event_id", "EVENT_NOT_FOUND")
    service = CalendarService(db, user_id)
    try:
        event = await service.get_event(uuid.UUID(event_id))
    except (ValueError, TypeError):
        event = None
    if not event:
        return _fail("未找到日程", "EVENT_NOT_FOUND")
    return _ok({"event": _build_event_data(event)})


async def get_current_time_tool(db: AsyncSession, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    return await get_current_time_impl(db, user_id, args)


async def parse_datetime_tool(db: AsyncSession, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    return await parse_datetime_impl(db, user_id, args)


async def query_calendar_events_tool(db: AsyncSession, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    return await query_calendar_events_impl(db, user_id, args)


async def check_time_conflict_tool(db: AsyncSession, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    return await check_time_conflict_impl(db, user_id, args)


async def detect_duplicate_events_tool(db: AsyncSession, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    return await detect_duplicate_events_impl(db, user_id, args)


async def suggest_available_slots_tool(db: AsyncSession, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    return await suggest_available_slots_impl(db, user_id, args)


async def add_calendar_event_tool(db: AsyncSession, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    return await add_calendar_event_impl(db, user_id, args)


async def delete_calendar_event_tool(db: AsyncSession, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    return await delete_calendar_event_impl(db, user_id, args)


async def update_calendar_event_tool(db: AsyncSession, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    return await update_calendar_event_impl(db, user_id, args)


async def create_reminder_tool(db: AsyncSession, user_id: str, args: dict[str, Any]) -> dict[str, Any]:
    return await create_reminder_impl(db, user_id, args)


def _wrap_tool(name: str, impl: Callable[..., Any]) -> Callable[..., Any]:
    async def _tool(*, payload: dict[str, Any]) -> ToolResponse:
        return _tool_response(await impl(payload["db"], payload["user_id"], payload["args"]))

    _tool.__name__ = name
    _tool.__doc__ = impl.__doc__
    return _tool


TOOL_REGISTRY: dict[str, Callable[..., Any]] = {
    "get_current_time": get_current_time_impl,
    "parse_datetime": parse_datetime_impl,
    "query_calendar_events": query_calendar_events_impl,
    "check_time_conflict": check_time_conflict_impl,
    "detect_duplicate_events": detect_duplicate_events_impl,
    "suggest_available_slots": suggest_available_slots_impl,
    "add_calendar_event": add_calendar_event_impl,
    "delete_calendar_event": delete_calendar_event_impl,
    "update_calendar_event": update_calendar_event_impl,
    "create_reminder": create_reminder_impl,
    "get_event_by_id": get_event_by_id_impl,
}


AGENT_TOOL_WRAPPERS: dict[str, Callable[..., Any]] = {
    name: _wrap_tool(name, impl) for name, impl in TOOL_REGISTRY.items()
}


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前时间和默认时区",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "parse_datetime",
            "description": "解析自然语言时间",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "current_time": {"type": "string"},
                    "timezone": {"type": "string"},
                    "duration_minutes": {"type": "number"},
                },
                "required": ["text", "current_time", "timezone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_calendar_events",
            "description": "查询日程，支持时间范围和关键词搜索",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_time": {"type": "string"},
                    "end_time": {"type": "string"},
                    "keyword": {"type": "string", "description": "按标题和描述模糊搜索"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_time_conflict",
            "description": "检查时间冲突",
            "parameters": {
                "type": "object",
                "properties": {"start_time": {"type": "string"}, "end_time": {"type": "string"}},
                "required": ["start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detect_duplicate_events",
            "description": "检测重复日程",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "start_time": {"type": "string"},
                    "end_time": {"type": "string"},
                },
                "required": ["title", "start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_available_slots",
            "description": "推荐可用时间段",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_time": {"type": "string"},
                    "end_time": {"type": "string"},
                    "duration_minutes": {"type": "number"},
                },
                "required": ["start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_calendar_event",
            "description": "添加日程",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "location": {"type": "string"},
                    "start_time": {"type": "string"},
                    "end_time": {"type": "string"},
                    "is_all_day": {"type": "boolean"},
                    "completed": {"type": "boolean"},
                    "force": {"type": "boolean"},
                    "allow_past": {"type": "boolean"},
                },
                "required": ["title", "start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_calendar_event",
            "description": "删除日程",
            "parameters": {
                "type": "object",
                "properties": {"event_id": {"type": "string"}},
                "required": ["event_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_calendar_event",
            "description": "修改日程",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "location": {"type": "string"},
                    "start_time": {"type": "string"},
                    "end_time": {"type": "string"},
                    "is_all_day": {"type": "boolean"},
                    "completed": {"type": "boolean"},
                },
                "required": ["event_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_reminder",
            "description": "创建提醒",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "location": {"type": "string"},
                    "start_time": {"type": "string"},
                    "end_time": {"type": "string"},
                    "force": {"type": "boolean"},
                },
                "required": ["start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_event_by_id",
            "description": "按ID查询单个日程详情",
            "parameters": {
                "type": "object",
                "properties": {"event_id": {"type": "string"}},
                "required": ["event_id"],
            },
        },
    },
]
