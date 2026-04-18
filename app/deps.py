from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Cookie, Depends, Header, HTTPException, Request

from app.config import Settings, get_settings


def get_settings_dep() -> Settings:
    return get_settings()


async def get_redis_dep():
    from app.services.redis_client import get_redis

    r = await get_redis()
    try:
        yield r
    finally:
        pass


async def get_session_id(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings_dep)],
    rb_session: Annotated[Optional[str], Cookie(alias="rb_session")] = None,
    x_session_id: Annotated[Optional[str], Header(alias="X-Session-ID")] = None,
) -> str:
    sid = rb_session or x_session_id
    if not sid:
        raise HTTPException(status_code=401, detail="Session required. POST /api/session first.")
    return sid


def client_rate_key(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"
