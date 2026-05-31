"""
Skill Router — 前置意图分流层。

对常见日程操作（增删查）直接执行，只走 1 次 LLM 调用来提取意图+实体。
复杂/不确定的意图自动降级给 ReActAgent。

不修改 ReActAgent 任何逻辑，只在 handle_text 入口前加一层分流。
"""
import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.calendar_service import CalendarService
from app.tools.calendar_tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)


class CalendarIntent(BaseModel):
    """LLM 结构化输出：意图 + 实体。"""
    intent: str = Field(
        description="操作类型: create_event | query_events | delete_event | update_event | toggle_complete | chat"
    )
    title: str = Field(default="", description="日程标题")
    start_time: str = Field(default="", description="开始时间 ISO 格式，如 2026-06-01T15:00:00")
    end_time: str = Field(default="", description="结束时间 ISO 格式")
    location: str = Field(default="", description="地点")
    description: str = Field(default="", description="描述")
    remind_enabled: bool = Field(default=False, description="是否开启提醒")
    date_query: str = Field(default="", description="查询日期，如 今天/明天/2026-06-01")
    event_reference: str = Field(default="", description="要操作的日程引用（标题或关键词）")
    confidence: str = Field(default="high", description="置信度: high | low")


# ── 兜底确认词检测（不走 LLM，直接命中） ──
CONFIRM_WORDS = {"确认", "好的", "好", "行", "可以", "是的", "对", "嗯", "确定", "没问题", "要", "继续", "是"}
CANCEL_WORDS = {"取消", "算了", "不要", "不用", "不了", "不"}
QUERY_KEYWORDS = {"查询", "查看", "有什么", "安排", "日程", "今天", "明天", "后天", "本周", "下周"}
DELETE_KEYWORDS = {"删除", "取消", "去掉", "移除", "删掉", "清除"}
TOGGLE_KEYWORDS = {"完成", "做完", "搞定", "结束", "标记"}

# 简单时间词 → 日期偏移
TIME_SIMPLE = {
    "今天": 0, "明天": 1, "后天": 2,
    "大后天": 3,
}


def _is_confirm(text: str) -> bool:
    return text.strip() in CONFIRM_WORDS


def _is_cancel(text: str) -> bool:
    return text.strip() in CANCEL_WORDS


def _detect_query_intent(text: str) -> Optional[str]:
    """快速检测查询意图，返回日期词或 None。"""
    for kw in QUERY_KEYWORDS:
        if kw in text:
            for time_word, offset in TIME_SIMPLE.items():
                if time_word in text:
                    dt = datetime.now() + timedelta(days=offset)
                    return dt.strftime("%Y-%m-%d")
            return datetime.now().strftime("%Y-%m-%d")
    return None


def _detect_delete_intent(text: str) -> Optional[str]:
    """快速检测删除意图，返回要删除的关键词。"""
    for kw in DELETE_KEYWORDS:
        if kw in text:
            # 提取关键词后面的内容作为事件引用
            idx = text.index(kw)
            ref = text[idx + len(kw):].strip()
            return ref if ref else text.replace(kw, "").strip()
    return None


def _detect_toggle_intent(text: str) -> Optional[str]:
    """快速检测完成/标记意图。"""
    for kw in TOGGLE_KEYWORDS:
        if kw in text:
            idx = text.index(kw)
            ref = text[idx + len(kw):].strip()
            return ref if ref else text.replace(kw, "").strip()
    return None


async def _classify_with_llm(text: str, model) -> Optional[CalendarIntent]:
    """用 LLM 做意图分类 + 实体提取（1 次调用）。"""
    from agentscope.message import Msg
    from agentscope.formatter import DashScopeChatFormatter

    formatter = DashScopeChatFormatter()
    prompt = await formatter.format([
        Msg("system", _INTENT_CLASSIFIER_PROMPT, "system"),
        Msg("user", text, "user"),
    ])

    try:
        res = await asyncio.wait_for(
            model(prompt, structured_model=CalendarIntent),
            timeout=3.0,
        )
        if res.metadata:
            intent = CalendarIntent(**res.metadata)
            logger.info("[Skill] LLM 分类结果 intent=%s confidence=%s", intent.intent, intent.confidence)
            return intent
    except (Exception, asyncio.TimeoutError) as exc:
        logger.warning("[Skill] LLM 分类失败，降级 ReActAgent: %s", exc)

    return None


async def _execute_create(db: AsyncSession, user_id: str, intent: CalendarIntent) -> dict:
    """执行创建日程 skill。"""
    args = {
        "title": intent.title,
        "start_time": intent.start_time,
        "end_time": intent.end_time,
    }
    if intent.location:
        args["location"] = intent.location
    if intent.description:
        args["description"] = intent.description

    result = await TOOL_REGISTRY["add_calendar_event"](db, user_id, args)

    if result.get("success"):
        return {
            "reply_text": f"✅ 已添加「{intent.title}」",
            "speech": None,
            "raw_msg": None,
            "need_confirm": False,
            "speech_streamed": False,
        }
    elif result.get("error_code") == "TIME_CONFLICT":
        conflicts = result.get("data", {}).get("conflicts", [])
        conflict_names = "、".join(c.get("title", "") for c in conflicts[:3])
        return {
            "reply_text": f"⚠️ 这个时间段已有「{conflict_names}」，还要继续添加吗？",
            "speech": None,
            "raw_msg": None,
            "need_confirm": True,
            "speech_streamed": False,
        }
    elif result.get("error_code") == "CONFIRM_REQUIRED":
        return {
            "reply_text": f"确认添加「{intent.title}」吗？",
            "speech": None,
            "raw_msg": None,
            "need_confirm": True,
            "speech_streamed": False,
        }
    else:
        return {
            "reply_text": result.get("message", "创建失败"),
            "speech": None,
            "raw_msg": None,
            "need_confirm": False,
            "speech_streamed": False,
        }


async def _execute_query(db: AsyncSession, user_id: str, intent: CalendarIntent) -> dict:
    """执行查询日程 skill。"""
    service = CalendarService(db, user_id)
    date_str = intent.date_query or intent.start_time[:10] if intent.start_time else datetime.now().strftime("%Y-%m-%d")

    # 解析日期范围
    try:
        query_date = datetime.fromisoformat(date_str[:10]) if date_str else datetime.now()
    except (ValueError, TypeError):
        query_date = datetime.now()

    start = query_date.replace(hour=0, minute=0, second=0)
    end = start + timedelta(days=1)

    events = await service.query_events(start_time=start, end_time=end)

    if not events:
        return {
            "reply_text": f"📭 {date_str[:10] if date_str else '今天'}没有日程。",
            "speech": None,
            "raw_msg": None,
            "need_confirm": False,
            "speech_streamed": False,
        }

    event_list = "、".join(
        f"{e.start_time.strftime('%H:%M') if e.start_time else ''} {e.title}"
        for e in events[:8]
    )
    return {
        "reply_text": f"📅 日程：{event_list}",
        "speech": None,
        "raw_msg": None,
        "need_confirm": False,
        "speech_streamed": False,
    }


async def _execute_delete(db: AsyncSession, user_id: str, intent: CalendarIntent) -> dict:
    """执行删除日程 skill（需确认）。"""
    service = CalendarService(db, user_id)
    ref = intent.event_reference or intent.title

    if not ref:
        return {}

    # 模糊匹配找日程
    events = await service.query_events(keyword=ref)
    active = [e for e in events if not e.completed]

    if not active:
        return {
            "reply_text": f"🔍 没找到「{ref}」相关的日程。",
            "speech": None,
            "raw_msg": None,
            "need_confirm": False,
            "speech_streamed": False,
        }

    target = active[0]
    result = await TOOL_REGISTRY["delete_calendar_event"](
        db, user_id,
        {"event_id": str(target.id), "confirm": True}
    )

    if result.get("success"):
        return {
            "reply_text": f"🗑️ 已删除「{target.title}」。",
            "speech": None,
            "raw_msg": None,
            "need_confirm": False,
            "speech_streamed": False,
        }
    elif result.get("error_code") == "CONFIRM_REQUIRED":
        preview = result.get("data", {}).get("preview", {})
        title = preview.get("title", ref)
        return {
            "reply_text": f"⚠️ 确认删除「{title}」吗？",
            "speech": None,
            "raw_msg": None,
            "need_confirm": True,
            "speech_streamed": False,
        }
    else:
        return {
            "reply_text": result.get("message", "删除失败"),
            "speech": None,
            "raw_msg": None,
            "need_confirm": False,
            "speech_streamed": False,
        }


async def route_with_skill(
    db: AsyncSession,
    user_id: str,
    text: str,
    model,
    pending_action: Optional[dict] = None,
) -> Optional[dict]:
    """
    尝试用 skill 路由处理用户输入。

    Returns:
        dict: 如果 skill 成功处理，返回结果字典（含 reply_text, need_confirm 等）。
        None: 降级，让调用方走 ReActAgent。
    """
    text_stripped = text.strip()

    # ── 快速路径：确认复用（不走 LLM） ──
    if _is_confirm(text_stripped) and pending_action:
        action = pending_action
        action["args"]["confirm"] = True
        result = await TOOL_REGISTRY[action["tool"]](db, user_id, action["args"])
        if result.get("success"):
            title = action["args"].get("title", "日程")
            return {
                "reply_text": f"好的，已处理「{title}」。",
                "speech": None, "raw_msg": None,
                "need_confirm": False, "speech_streamed": False,
            }
        return {
            "reply_text": result.get("message", "操作失败"),
            "speech": None, "raw_msg": None,
            "need_confirm": False, "speech_streamed": False,
        }

    # ── 快速路径：取消（不走 LLM） ──
    if _is_cancel(text_stripped):
        return {
            "reply_text": "好的，已取消。",
            "speech": None, "raw_msg": None,
            "need_confirm": False, "speech_streamed": False,
        }

    # ── LLM 分类 ──
    intent = await _classify_with_llm(text_stripped, model)
    if intent is None or intent.confidence == "low":
        logger.info("[Skill] 置信度低或分类失败，降级 ReActAgent")
        return None

    logger.info("[Skill] 命中 intent=%s", intent.intent)

    # ── 按意图执行 ──
    if intent.intent == "create_event":
        return await _execute_create(db, user_id, intent)
    elif intent.intent == "query_events":
        return await _execute_query(db, user_id, intent)
    elif intent.intent == "delete_event":
        return await _execute_delete(db, user_id, intent)
    elif intent.intent in ("update_event", "toggle_complete"):
        # 复杂操作降级给 ReActAgent
        logger.info("[Skill] %s 降级 ReActAgent", intent.intent)
        return None
    else:
        # chat / 未知 → 降级
        return None


async def get_pending_action(db: AsyncSession, user_id: str) -> Optional[dict]:
    """查询是否有待确认的操作（目前简单实现，后续可存 Redis）。"""
    return None


# ── System Prompt ──

_INTENT_CLASSIFIER_PROMPT = """你是一个日程意图分类器。分析用户输入，输出 JSON。

## 时间解析规则
- 当前时间会在用户消息中标注。将自然语言时间转为 ISO 8601 格式。
- "明天下午三点" → 日期+1, T15:00:00
- "下周一下午两点" → 找到下周一的日期, T14:00:00
- 如果用户没有指定具体时间，使用默认时间段（如会议默认 1 小时）。
- 日程不需要 end_time 时可以留空。

## 意图类型
- create_event: 创建新日程
- query_events: 查询某天的日程
- delete_event: 删除日程
- update_event: 修改日程
- toggle_complete: 标记完成/未完成
- chat: 闲聊、问候或不明确的请求

## 置信度
- high: 信息完整，可以直接执行
- low: 信息模糊，需要进一步确认或交给 ReActAgent

## 示例
用户: "明天下午三点开会讨论项目进度"
→ {"intent":"create_event","title":"讨论项目进度","start_time":"<明天日期>T15:00:00","confidence":"high"}

用户: "今天有什么安排"
→ {"intent":"query_events","date_query":"今天","confidence":"high"}

用户: "你好"
→ {"intent":"chat","confidence":"high"}

只输出 JSON，不要其他内容。"""
