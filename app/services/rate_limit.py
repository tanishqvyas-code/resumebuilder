from __future__ import annotations

import time
from collections import defaultdict

import redis.asyncio as redis

from app.config import Settings, get_settings

_MEM_COUNTS: dict[str, int] = defaultdict(int)


async def check_ai_rate_limit(
    r: redis.Redis,
    client_key: str,
    settings: Settings | None = None,
) -> tuple[bool, int]:
    """
    Sliding window using a single minute bucket key (simple, good enough for demos).
    Returns (allowed, remaining).
    """
    s = settings or get_settings()
    bucket = int(time.time()) // s.ai_rate_window_seconds
    key = f"rate:ai:{client_key}:{bucket}"
    try:
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, s.ai_rate_window_seconds + 2)
        results = await pipe.execute()
        count = int(results[0])
    except Exception:
        _MEM_COUNTS[key] += 1
        count = _MEM_COUNTS[key]
    limit = s.ai_rate_limit_per_minute
    remaining = max(0, limit - count)
    return count <= limit, remaining
