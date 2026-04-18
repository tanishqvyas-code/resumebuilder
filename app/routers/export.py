from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from redis.asyncio import Redis

from app.deps import get_redis_dep, get_session_id
from app.models.resume import ResumeData
from app.services.export_docx import resume_to_docx
from app.services.export_pdf import resume_to_pdf_bytes
from app.services import resume_store
from app.services.render_resume import render_resume_html

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/export", tags=["export"])


async def _load_data(r: Redis, session_id: str) -> ResumeData:
    env = await resume_store.load_resume(r, session_id)
    if env is None:
        return ResumeData()
    return env.resume


@router.get("/html", response_class=HTMLResponse)
async def export_html(
    session_id: Annotated[str, Depends(get_session_id)],
    r: Annotated[Redis, Depends(get_redis_dep)],
) -> HTMLResponse:
    data = await _load_data(r, session_id)
    html = render_resume_html(data)
    return HTMLResponse(content=html)


@router.get("/pdf")
async def export_pdf(
    session_id: Annotated[str, Depends(get_session_id)],
    r: Annotated[Redis, Depends(get_redis_dep)],
) -> Response:
    data = await _load_data(r, session_id)
    try:
        pdf = resume_to_pdf_bytes(data)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    filename = _safe_filename(data.personal.full_name or "resume") + ".pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/docx")
async def export_docx(
    session_id: Annotated[str, Depends(get_session_id)],
    r: Annotated[Redis, Depends(get_redis_dep)],
) -> Response:
    data = await _load_data(r, session_id)
    try:
        buf = resume_to_docx(data)
    except RuntimeError as e:
        raise HTTPException(status_code=501, detail=str(e)) from e
    filename = _safe_filename(data.personal.full_name or "resume") + ".docx"
    return Response(
        content=buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _safe_filename(name: str) -> str:
    out = "".join(c for c in name.strip() if c.isalnum() or c in (" ", "-", "_")).strip()
    return out.replace(" ", "_") or "resume"
