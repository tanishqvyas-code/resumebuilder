from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from redis.asyncio import Redis

from app.deps import get_redis_dep, get_session_id
from app.models.resume import ResumeData, ResumeEnvelope
from app.services import resume_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["resume"])


@router.get("/resume", response_model=ResumeEnvelope)
async def get_resume(
    session_id: Annotated[str, Depends(get_session_id)],
    r: Annotated[Redis, Depends(get_redis_dep)],
) -> ResumeEnvelope:
    env = await resume_store.load_resume(r, session_id)
    if env is None:
        return ResumeEnvelope(resume=ResumeData())
    await resume_store.touch_session(r, session_id)
    return env


@router.put("/resume", response_model=ResumeEnvelope)
async def put_resume(
    body: ResumeData,
    session_id: Annotated[str, Depends(get_session_id)],
    r: Annotated[Redis, Depends(get_redis_dep)],
) -> ResumeEnvelope:
    return await resume_store.save_resume(r, session_id, body)


@router.patch("/resume", response_model=ResumeEnvelope)
async def patch_resume(
    body: ResumeData,
    session_id: Annotated[str, Depends(get_session_id)],
    r: Annotated[Redis, Depends(get_redis_dep)],
) -> ResumeEnvelope:
    """Merge-friendly: replaces document with provided body (client sends full state)."""
    return await resume_store.save_resume(r, session_id, body)
