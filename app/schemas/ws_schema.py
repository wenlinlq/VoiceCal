from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field


class TextMessage(BaseModel):
    type: Literal["text.message"] = "text.message"
    session_id: str
    text: str


class AudioChunk(BaseModel):
    type: Literal["audio.chunk"] = "audio.chunk"
    session_id: str
    data: str  # base64 encoded audio


class AudioEnd(BaseModel):
    type: Literal["audio.end"] = "audio.end"
    session_id: str


WSClientMessage = Union[TextMessage, AudioChunk, AudioEnd]


class AgentReply(BaseModel):
    type: Literal["agent.reply"] = "agent.reply"
    text: str
    intent: Optional[str] = None
    slots: Optional[dict[str, Any]] = None
    need_confirm: bool = False


class TurnDone(BaseModel):
    type: Literal["turn.done"] = "turn.done"
    success: bool


class TranscriptionResult(BaseModel):
    type: Literal["transcription"] = "transcription"
    text: str


class TTSChunkMessage(BaseModel):
    type: Literal["tts.chunk"] = "tts.chunk"
    data: str  # base64 encoded PCM audio
    is_last: bool = False


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    message: str


WSServerMessage = Union[AgentReply, TurnDone, TranscriptionResult, TTSChunkMessage, ErrorMessage]
