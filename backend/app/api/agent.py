from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.calendar_agent import CalendarAgent
from app.db.database import get_db
from app.schemas.agent_schema import TextRequest, TextResponse

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
):
    result = await agent.process_text(
        db=db,
        user_id=req.user_id,
        session_id=req.session_id,
        text=req.text,
    )
    return TextResponse(**result)
