from typing import Any

from pydantic import BaseModel


class APIResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: Any = None

    @classmethod
    def success(cls, data: Any = None, message: str = "ok") -> "APIResponse":
        return cls(code=0, message=message, data=data)

    @classmethod
    def error(cls, code: int = -1, message: str = "error", data: Any = None) -> "APIResponse":
        return cls(code=code, message=message, data=data)
