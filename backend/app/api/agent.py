import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.calendar_agent import CalendarAgent
from app.core.auth import get_current_user
from app.db.database import get_db
from app.schemas.agent_schema import TextRequest, TextResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])

_agent = None


def get_agent() -> CalendarAgent:
    global _agent
    if _agent is None:
        _agent = CalendarAgent()
    return _agent


@router.post("/text", response_model=TextResponse)
async def text_agent(
    req: TextRequest,
    db: AsyncSession = Depends(get_db),
    agent: CalendarAgent = Depends(get_agent),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["openid"]
    logger.info("[Agent] 文本调试请求 user_id=%s session_id=%s", user_id, req.session_id)
    result = await agent.process_text(
        db=db,
        user_id=user_id,
        session_id=req.session_id,
        text=req.text,
    )
    return TextResponse(**result)
