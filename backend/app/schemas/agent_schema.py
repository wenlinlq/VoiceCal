from typing import Any, Optional

from pydantic import BaseModel, Field


class TextRequest(BaseModel):
    session_id: str = Field(..., description="会话 ID")
    user_id: str = Field("demo_user", description="用户 ID")
    text: str = Field(..., description="用户输入文本")


class ToolCallResult(BaseModel):
    name: str
    args: dict[str, Any]
    result: dict[str, Any]


class TextResponse(BaseModel):
    session_id: str
    intent: str = ""
    slots: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[ToolCallResult] = Field(default_factory=list)
    reply_text: str = ""
