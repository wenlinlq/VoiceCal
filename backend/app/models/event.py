import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    is_all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    # 提醒与推送
    remind_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    remind_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    push_status: Mapped[str] = mapped_column(String(32), default="pending")  # pending / sent / failed / no_auth / expired
    pushed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    subscribe_template_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
