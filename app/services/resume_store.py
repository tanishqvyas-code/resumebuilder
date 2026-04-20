from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as redis

from app.config import Settings, get_settings
from app.models.resume import ResumeData, ResumeEnvelope

logger = logging.getLogger(__name__)
_MEM_DRAFTS: dict[str, ResumeEnvelope] = {}


def _key(session_id: str) -> str:
    return f"resume:draft:{session_id}"


async def save_resume(
    r: redis.Redis,
    session_id: str,
    data: ResumeData,
    settings: Settings | None = None,
) -> ResumeEnvelope:
    s = settings or get_settings()
    env = ResumeEnvelope(
        resume=data,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    payload = env.json()
    try:
        await r.set(_key(session_id), payload, ex=s.session_ttl_seconds)
    except Exception as e:
        logger.warning("Redis unavailable, using in-memory draft store: %s", e)
        _MEM_DRAFTS[session_id] = env
    return env


async def load_resume(
    r: redis.Redis,
    session_id: str,
) -> Optional[ResumeEnvelope]:
    try:
        raw = await r.get(_key(session_id))
        if not raw:
            return _MEM_DRAFTS.get(session_id)
        return ResumeEnvelope.parse_raw(raw)
    except Exception as e:
        logger.warning("Redis read failed, falling back to in-memory draft store: %s", e)
        return _MEM_DRAFTS.get(session_id)


async def touch_session(r: redis.Redis, session_id: str, settings: Settings | None = None) -> None:
    s = settings or get_settings()
    key = _key(session_id)
    try:
        if await r.exists(key):
            await r.expire(key, s.session_ttl_seconds)
    except Exception:
        # In-memory fallback does not currently apply TTLs.
        pass
        