import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.response import APIResponse
from app.db.database import get_db
from app.schemas.event_schema import EventCreate, EventResponse, EventUpdate
from app.services.calendar_service import CalendarService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("", response_model=APIResponse)
async def list_events(
    start: Optional[datetime] = Query(None, description="查询开始时间（ISO 8601）"),
    end: Optional[datetime] = Query(None, description="查询结束时间（ISO 8601）"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["openid"]
    logger.info("[日程] 查询日程列表 user_id=%s", user_id)
    service = CalendarService(db, user_id)
    events = await service.query_events(start_time=start, end_time=end)
    return APIResponse.success(data=[EventResponse.model_validate(e).model_dump(mode="json") for e in events])


@router.post("", response_model=APIResponse)
async def create_event(
    body: EventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["openid"]
    service = CalendarService(db, user_id)
    event = await service.create_event(body)
    logger.info("[日程] 创建日程 user_id=%s event_id=%s", user_id, event.id)
    return APIResponse.success(
        data=EventResponse.model_validate(event).model_dump(mode="json"),
        message="日程已创建",
    )


@router.get("/{event_id}", response_model=APIResponse)
async def get_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["openid"]
    service = CalendarService(db, user_id)
    event = await service.get_event(event_id)
    if not event:
        logger.warning("[日程] 查询失败，日程不存在 user_id=%s event_id=%s", user_id, event_id)
        return APIResponse.error(code=404, message="日程不存在")
    return APIResponse.success(data=EventResponse.model_validate(event).model_dump(mode="json"))


@router.put("/{event_id}", response_model=APIResponse)
async def update_event(
    event_id: uuid.UUID,
    body: EventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["openid"]
    service = CalendarService(db, user_id)
    event = await service.update_event(event_id, body)
    if not event:
        logger.warning("[日程] 修改失败，日程不存在 user_id=%s event_id=%s", user_id, event_id)
        return APIResponse.error(code=404, message="日程不存在")
    logger.info("[日程] 修改日程 user_id=%s event_id=%s", user_id, event_id)
    return APIResponse.success(
        data=EventResponse.model_validate(event).model_dump(mode="json"),
        message="日程已更新",
    )


@router.delete("/{event_id}", response_model=APIResponse)
async def delete_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["openid"]
    service = CalendarService(db, user_id)
    deleted = await service.delete_event(event_id)
    if not deleted:
        logger.warning("[日程] 删除失败，日程不存在 user_id=%s event_id=%s", user_id, event_id)
        return APIResponse.error(code=404, message="日程不存在")
    logger.info("[日程] 删除日程 user_id=%s event_id=%s", user_id, event_id)
    return APIResponse.success(message="日程已删除")
