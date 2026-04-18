from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.config import Settings, get_settings

router = APIRouter(prefix="/api", tags=["session"])


@router.post("/session")
async def create_session(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    session_id = str(uuid.uuid4())
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=settings.session_ttl_seconds,
        path="/",
    )
    return {"session_id": session_id, "ok": True}
