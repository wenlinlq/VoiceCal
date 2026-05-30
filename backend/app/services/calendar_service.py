"""
日历服务 — 日程 CRUD 操作。

封装对 events 表的所有数据库操作，提供创建、查询、更新、删除功能。
所有操作按 user_id 隔离。
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.schemas.event_schema import EventCreate, EventUpdate

logger = logging.getLogger(__name__)
LOCAL_TIMEZONE = timezone(timedelta(hours=8))


def _to_local_naive(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(LOCAL_TIMEZONE).replace(tzinfo=None)


class CalendarService:
    """日历 CRUD 服务，封装对 events 表的数据库操作。"""

    def __init__(self, db: AsyncSession, user_id: str):
        """
        Args:
            db: SQLAlchemy 异步数据库会话。
            user_id: 用户标识（openid）。
        """
        self.db = db
        self.user_id = user_id
        logger.info("[日历服务] 初始化 user_id=%s", user_id)

    async def create_event(self, data: EventCreate) -> Event:
        """
        创建新日程。

        Args:
            data: 日程创建数据（标题、时间范围等）。

        Returns:
            Event: 创建后的日程对象（含数据库生成的 id）。
        """
        logger.info(
            "[日历服务] 创建日程 标题=%s 开始时间=%s 结束时间=%s",
            data.title,
            data.start_time.isoformat(),
            data.end_time.isoformat(),
        )
        event_data = data.model_dump()
        event_data["start_time"] = _to_local_naive(data.start_time)
        event_data["end_time"] = _to_local_naive(data.end_time)
        event = Event(user_id=self.user_id, **event_data)
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        logger.info("[日历服务] 创建完成 event_id=%s", event.id)
        return event

    async def query_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        keyword: Optional[str] = None,
    ) -> list[Event]:
        """
        查询日程列表，支持时间范围过滤和关键词搜索。

        Args:
            start_time: 查询开始时间。
            end_time: 查询结束时间。
            keyword: 关键词，模糊匹配标题和描述。

        Returns:
            list[Event]: 符合条件的日程列表，按开始时间排序。
        """
        logger.info(
            "[日历服务] 查询日程 开始=%s 结束=%s 关键词=%s",
            start_time.isoformat() if start_time else "不限",
            end_time.isoformat() if end_time else "不限",
            keyword or "无",
        )
        local_start_time = _to_local_naive(start_time)
        local_end_time = _to_local_naive(end_time)
        stmt = select(Event).where(Event.user_id == self.user_id)
        if local_start_time:
            stmt = stmt.where(Event.end_time >= local_start_time)
        if local_end_time:
            stmt = stmt.where(Event.start_time <= local_end_time)
        if keyword:
            pattern = f"%{keyword}%"
            from sqlalchemy import or_
            stmt = stmt.where(or_(Event.title.ilike(pattern), Event.description.ilike(pattern)))
        stmt = stmt.order_by(Event.start_time)
        result = await self.db.execute(stmt)
        events = list(result.scalars().all())
        logger.info("[日历服务] 查询完成 数量=%s", len(events))
        return events

    async def get_event(self, event_id: uuid.UUID) -> Optional[Event]:
        """按 ID 查询单个日程。"""
        stmt = select(Event).where(
            Event.id == event_id, Event.user_id == self.user_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_event(self, event_id: uuid.UUID, data: EventUpdate) -> Optional[Event]:
        """
        更新已有日程。只更新传入的非空字段。

        Args:
            event_id: 日程 ID。
            data: 需要更新的字段。

        Returns:
            Event | None: 更新后的日程对象，日程不存在时返回 None。
        """
        event = await self.get_event(event_id)
        if not event:
            logger.warning("[日历服务] 更新失败，日程不存在 event_id=%s", event_id)
            return None
        update_dict = data.model_dump(exclude_unset=True)
        logger.info(
            "[日历服务] 修改日程 event_id=%s 更新字段=%s",
            event_id,
            list(update_dict.keys()),
        )
        if "start_time" in update_dict:
            update_dict["start_time"] = _to_local_naive(update_dict["start_time"])
        if "end_time" in update_dict:
            update_dict["end_time"] = _to_local_naive(update_dict["end_time"])
        for field, value in update_dict.items():
            setattr(event, field, value)
        await self.db.commit()
        await self.db.refresh(event)
        logger.info("[日历服务] 修改完成 event_id=%s", event_id)
        return event

    async def delete_event(self, event_id: uuid.UUID) -> bool:
        """
        删除日程（硬删除）。

        Args:
            event_id: 日程 ID。

        Returns:
            bool: 删除成功返回 True，日程不存在返回 False。
        """
        event = await self.get_event(event_id)
        if not event:
            logger.warning("[日历服务] 删除失败，日程不存在 event_id=%s", event_id)
            return False
        logger.info("[日历服务] 删除日程 event_id=%s 标题=%s", event_id, event.title)
        await self.db.delete(event)
        await self.db.commit()
        logger.info("[日历服务] 删除完成 event_id=%s", event_id)
        return True
