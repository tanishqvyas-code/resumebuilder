from __future__ import annotations

import logging
from typing import Optional

import redis.asyncio as redis

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

_pool: Optional[redis.ConnectionPool] = None


async def get_redis_pool(settings: Settings | None = None) -> redis.ConnectionPool:
    global _pool
    if _pool is None:
        s = settings or get_settings()
        _pool = redis.ConnectionPool.from_url(
            s.redis_url,
            decode_responses=True,
            max_connections=50,
        )
    return _pool


async def get_redis() -> redis.Redis:
    pool = await get_redis_pool()
    return redis.Redis(connection_pool=pool)


async def close_redis() -> None:
    global _pool
    if _pool is not None:
        await _pool.disconnect()
        _pool = None
        logger.info("Redis pool closed")
