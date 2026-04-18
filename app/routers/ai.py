from __future__ import annotations

import logging
from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from redis.asyncio import Redis

from app.config import Settings, get_settings
from app.deps import client_rate_key, get_redis_dep, get_session_id
from app.models.ai import (
    AtsScoreRequest,
    BulletsRequest,
    ProjectDescriptionRequest,
    RephraseRequest,
    SkillsSuggestRequest,
    SummaryRequest,
)
from app.services import ats_scorer, gemini_service, rate_limit, resume_store
from app.models.resume import ResumeData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai"])


async def _guard_ai(
    request: Request,
    r: Redis,
    settings: Settings,
) -> None:
    ok, remaining = await rate_limit.check_ai_rate_limit(r, client_rate_key(request), settings)
    if not ok:
        raise HTTPException(status_code=429, detail="AI rate limit exceeded. Try again shortly.")


@router.post("/summary")
async def ai_summary(
    body: SummaryRequest,
    request: Request,
    session_id: Annotated[str, Depends(get_session_id)],
    r: Annotated[Redis, Depends(get_redis_dep)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    await _guard_ai(request, r, settings)
    try:
        text = await gemini_service.generate_summary(
            body.target_role,
            body.years_experience,
            body.key_skills,
            body.highlights,
            body.current_summary,
            settings,
        )
        return {"summary": text}
    except RuntimeError as e:
        logger.warning("Gemini summary: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.exception("Gemini summary failed")
        raise HTTPException(status_code=503, detail="AI service unavailable") from e


@router.post("/bullets")
async def ai_bullets(
    body: BulletsRequest,
    request: Request,
    session_id: Annotated[str, Depends(get_session_id)],
    r: Annotated[Redis, Depends(get_redis_dep)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    await _guard_ai(request, r, settings)
    try:
        bullets = await gemini_service.improve_bullets(body.context, body.bullets, settings)
        return {"bullets": bullets}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.exception("Gemini bullets failed")
        raise HTTPException(status_code=503, detail="AI service unavailable") from e


@router.post("/skills")
async def ai_skills(
    body: SkillsSuggestRequest,
    request: Request,
    session_id: Annotated[str, Depends(get_session_id)],
    r: Annotated[Redis, Depends(get_redis_dep)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    await _guard_ai(request, r, settings)
    try:
        text = await gemini_service.suggest_skills(body.job_role, body.industry, body.existing_skills, settings)
        return {"skills": text}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.exception("Gemini skills failed")
        raise HTTPException(status_code=503, detail="AI service unavailable") from e


@router.post("/rephrase")
async def ai_rephrase(
    body: RephraseRequest,
    request: Request,
    session_id: Annotated[str, Depends(get_session_id)],
    r: Annotated[Redis, Depends(get_redis_dep)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    await _guard_ai(request, r, settings)
    try:
        text = await gemini_service.rephrase_ats(body.text, body.context, settings)
        return {"text": text}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.exception("Gemini rephrase failed")
        raise HTTPException(status_code=503, detail="AI service unavailable") from e


@router.post("/project-description")
async def ai_project_description(
    body: ProjectDescriptionRequest,
    request: Request,
    session_id: Annotated[str, Depends(get_session_id)],
    r: Annotated[Redis, Depends(get_redis_dep)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    await _guard_ai(request, r, settings)
    try:
        text = await gemini_service.enhance_project_description(body.text, body.technologies, settings)
        return {"description": text}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.exception("Gemini project description failed")
        raise HTTPException(status_code=503, detail="AI service unavailable") from e


@router.post("/ats-score")
async def ai_ats_score(
    body: AtsScoreRequest,
    session_id: Annotated[str, Depends(get_session_id)],
    r: Annotated[Redis, Depends(get_redis_dep)],
) -> dict:
    if body.resume_data:
        try:
            data = ResumeData(**body.resume_data)
        except Exception as e:
            raise HTTPException(status_code=422, detail="Invalid resume_data payload.") from e
    else:
        env = await resume_store.load_resume(r, session_id)
        data = env.resume if env else ResumeData()
    result = ats_scorer.score_resume(
        data,
        target_role=body.target_role,
        job_description=body.job_description,
    )
    return result


@router.post("/ats-score-upload")
async def ai_ats_score_upload(
    file: UploadFile = File(...),
    target_role: str = Form(""),
    job_description: str = Form(""),
) -> dict:
    filename = (file.filename or "").lower()
    content_type = (file.content_type or "").lower()
    if not filename.endswith(".pdf") and "pdf" not in content_type:
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max supported size is 8MB.")

    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(raw))
        text_chunks = []
        for page in reader.pages:
            extracted = page.extract_text() or ""
            if extracted.strip():
                text_chunks.append(extracted)
        extracted_text = "\n".join(text_chunks)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Could not read PDF text. Upload a text-based PDF.") from e

    result = ats_scorer.score_resume_text(
        extracted_text,
        target_role=target_role,
        job_description=job_description,
    )
    result["source"] = "uploaded_pdf"
    return result
