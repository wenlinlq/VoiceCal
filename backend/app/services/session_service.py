import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    session_id: str
    user_id: str = "demo_user"
    connected: bool = True
    pending_action: Optional[str] = None
    pending_event: Optional[dict[str, Any]] = None
    reason: Optional[str] = None
    candidates: list[dict[str, Any]] = field(default_factory=list)
    last_user_intent: Optional[str] = None
    last_user_text: Optional[str] = None
    last_tool_result: Optional[dict[str, Any]] = None


class SessionService:
    TTL_SECONDS = 3600
    KEY_PREFIX = "voicecal:session:"

    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None
        self._fallback: dict[str, SessionState] = {}

    async def _ensure_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            self._redis = aioredis.from_url(settings.redis_url, decode_responses=False)
            await self._redis.ping()
            logger.info("session service: connected to Redis")
        except Exception as e:
            logger.warning("session service: Redis unavailable (%s), using in-memory", e)
            self._redis = False  # mark as unavailable
        return self._redis

    async def register(self, session_id: str, user_id: str = "demo_user") -> SessionState:
        existing = await self.get(session_id)
        if existing:
            return await self.set_state(session_id, connected=True, user_id=user_id)

        state = SessionState(session_id=session_id, user_id=user_id)
        r = await self._ensure_redis()
        if r:
            key = self.KEY_PREFIX + session_id
            await r.set(key, json.dumps(asdict(state)), ex=self.TTL_SECONDS)
            logger.info("session registered (redis): %s user_id=%s", session_id, user_id)
        else:
            self._fallback[session_id] = state
            logger.info("session registered (memory): %s user_id=%s", session_id, user_id)
        return state

    async def get(self, session_id: str) -> Optional[SessionState]:
        r = await self._ensure_redis()
        if r:
            key = self.KEY_PREFIX + session_id
            try:
                data = await r.get(key)
                if data:
                    return SessionState(**json.loads(data))
            except Exception as exc:
                logger.warning("session service: Redis read failed (%s), using memory fallback", exc)
                return self._fallback.get(session_id)
            return self._fallback.get(session_id)
        return self._fallback.get(session_id)

    async def remove(self, session_id: str):
        r = await self._ensure_redis()
        if r:
            key = self.KEY_PREFIX + session_id
            await r.delete(key)
            logger.info("session removed (redis): %s", session_id)
        else:
            self._fallback.pop(session_id, None)
            logger.info("session removed (memory): %s", session_id)

    async def set_state(self, session_id: str, **kwargs) -> SessionState:
        state = await self.get(session_id) or SessionState(session_id=session_id)
        for key, value in kwargs.items():
            setattr(state, key, value)
        r = await self._ensure_redis()
        if r:
            key = self.KEY_PREFIX + session_id
            try:
                await r.set(key, json.dumps(asdict(state)), ex=self.TTL_SECONDS)
            except Exception as exc:
                logger.warning("session service: Redis write failed (%s), using memory fallback", exc)
                self._fallback[session_id] = state
        else:
            self._fallback[session_id] = state
        logger.info("session state updated: %s %s", session_id, kwargs)
        return state

    async def clear_pending(self, session_id: str) -> SessionState:
        return await self.set_state(
            session_id,
            pending_action=None,
            pending_event=None,
            reason=None,
            candidates=[],
            last_tool_result=None,
        )

    async def update_last_interaction(
        self,
        session_id: str,
        *,
        last_user_text: Optional[str] = None,
        last_user_intent: Optional[str] = None,
        last_tool_result: Optional[dict[str, Any]] = None,
    ) -> SessionState:
        updates: dict[str, Any] = {}
        if last_user_text is not None:
            updates["last_user_text"] = last_user_text
        if last_user_intent is not None:
            updates["last_user_intent"] = last_user_intent
        if last_tool_result is not None:
            updates["last_tool_result"] = last_tool_result
        if updates:
            return await self.set_state(session_id, **updates)
        return await self.get(session_id) or SessionState(session_id=session_id)

    async def apply_pending_update(
        self,
        session_id: str,
        *,
        pending_action: Optional[str] = None,
        pending_event: Optional[dict[str, Any]] = None,
        reason: Optional[str] = None,
        candidates: Optional[list[dict[str, Any]]] = None,
        last_user_text: Optional[str] = None,
        last_user_intent: Optional[str] = None,
        last_tool_result: Optional[dict[str, Any]] = None,
    ) -> SessionState:
        updates: dict[str, Any] = {}
        if pending_action is not None:
            updates["pending_action"] = pending_action
        if pending_event is not None:
            updates["pending_event"] = pending_event
        if reason is not None:
            updates["reason"] = reason
        if candidates is not None:
            updates["candidates"] = candidates
        if last_user_text is not None:
            updates["last_user_text"] = last_user_text
        if last_user_intent is not None:
            updates["last_user_intent"] = last_user_intent
        if last_tool_result is not None:
            updates["last_tool_result"] = last_tool_result
        return await self.set_state(session_id, **updates)

    @property
    def active_count(self) -> int:
        return len(self._fallback)


session_service = SessionService()
