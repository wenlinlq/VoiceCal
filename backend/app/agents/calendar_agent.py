"""
兼容旧 `/api/agent/text` 调试接口的适配层。

实际智能行为统一复用 app/services/agent_service.py 中的 AgentScope 主链路。
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agent_service import CalendarAgentService


class CalendarAgent:
    def __init__(self):
        self.service = CalendarAgentService()

    async def process_text(
        self,
        db: AsyncSession,
        user_id: str,
        session_id: str,
        text: str,
    ) -> dict[str, Any]:
        result = await self.service.handle_text(
            db=db,
            user_id=user_id,
            session_id=session_id,
            text=text,
        )
        return {
            "session_id": session_id,
            "intent": "agent_scope",
            "slots": {},
            "tool_calls": [],
            "reply_text": result["reply_text"],
        }
