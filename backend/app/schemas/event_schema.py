import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    title: str = Field(..., max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    location: Optional[str] = Field(None, max_length=500)
    start_time: datetime
    end_time: datetime
    is_all_day: bool = False
    remind_at: Optional[datetime] = None
    remind_enabled: bool = False
    subscribe_template_id: Optional[str] = Field(None, max_length=128)


class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    location: Optional[str] = Field(None, max_length=500)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_all_day: Optional[bool] = None
    remind_at: Optional[datetime] = None
    remind_enabled: Optional[bool] = None
    push_status: Optional[str] = Field(None, max_length=32)
    subscribe_template_id: Optional[str] = Field(None, max_length=128)


class EventResponse(BaseModel):
    id: uuid.UUID
    user_id: str
    title: str
    description: Optional[str]
    location: Optional[str]
    start_time: datetime
    end_time: datetime
    is_all_day: bool
    remind_at: Optional[datetime] = None
    remind_enabled: bool = False
    push_status: str = "pending"
    pushed_at: Optional[datetime] = None
    subscribe_template_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
