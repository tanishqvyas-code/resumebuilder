from __future__ import annotations

import logging
import re
from typing import Optional

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def _extract_gemini_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except Exception:
        return (response.text or "").strip() or f"HTTP {response.status_code}"

    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, dict):
            message = err.get("message")
            status = err.get("status")
            code = err.get("code")
            if message and status:
                return f"{status} ({code}): {message}" if code else f"{status}: {message}"
            if message:
                return str(message)
    return (response.text or "").strip() or f"HTTP {response.status_code}"


async def _generate(settings: Settings, prompt: str) -> str:
    if not settings.gemini_api_key:
        raise RuntimeError("Gemini API key missing. Set GEMINI_API_KEY (or GOOGLE_API_KEY).")

    url = f"{GEMINI_BASE_URL}/models/{settings.gemini_model}:generateContent"
    params = {"key": settings.gemini_api_key}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    timeout = httpx.Timeout(20.0, connect=10.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, params=params, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        detail = _extract_gemini_error(e.response)
        logger.warning("Gemini HTTP error: %s", detail)
        raise RuntimeError(f"Gemini API request failed: {detail}") from e
    except httpx.HTTPError as e:
        raise RuntimeError(f"Gemini API unavailable: {e}") from e

    parts: list[str] = []
    for cand in data.get("candidates", []) or []:
        content = cand.get("content", {}) or {}
        for part in content.get("parts", []) or []:
            text = part.get("text")
            if text:
                parts.append(text)
    return "\n".join(parts).strip()


def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    return t.strip()


async def generate_summary(
    target_role: str,
    years_experience: str,
    key_skills: str,
    highlights: str,
    current_summary: str,
    settings: Settings | None = None,
) -> str:
    s = settings or get_settings()
    prompt = f"""You are an expert resume writer for ATS systems.

Write a professional summary of 2-4 short lines (plain text only, no headings, no bullet symbols).
Use strong keywords for the role. No first-person pronouns. No tables or markdown.

Target role: {target_role or "Not specified"}
Years of experience: {years_experience or "Not specified"}
Key skills: {key_skills or "Not specified"}
Career highlights: {highlights or "Not specified"}
Current draft (rewrite/improve if helpful): {current_summary or "None"}

Output only the summary paragraphs, separated by blank lines if needed."""
    return _clean_text(await _generate(s, prompt))


async def improve_bullets(context: str, bullets: list[str], settings: Settings | None = None) -> list[str]:
    s = settings or get_settings()
    joined = "\n".join(f"- {b}" for b in bullets if b.strip())
    prompt = f"""Rewrite these resume bullet points for ATS and hiring managers.
Rules: start with strong action verbs; add measurable impact where plausible; stay truthful; do not invent employers or numbers not implied.
Return ONLY a plain bulleted list using hyphen-minus (- ) at line start, one bullet per line.
Context (job/project): {context or "General"}
Original:
{joined or "(empty)"}"""
    return _parse_bullet_lines(await _generate(s, prompt))


async def suggest_skills(
    job_role: str,
    industry: str,
    existing_skills: str,
    settings: Settings | None = None,
) -> str:
    s = settings or get_settings()
    prompt = f"""Suggest ATS-relevant skills for this candidate focus.
Return a comma-separated list only (no sentences, no numbering), max 25 items, prioritize hard skills and tools.

Job role: {job_role or "Not specified"}
Industry: {industry or "Not specified"}
Already has: {existing_skills or "None"}"""
    return _clean_text(await _generate(s, prompt))


async def rephrase_ats(text: str, context: str, settings: Settings | None = None) -> str:
    s = settings or get_settings()
    prompt = f"""Rephrase for ATS-friendly, concise professional resume text.
No markdown, no tables, no special symbols. Plain sentences or short lines.

Context: {context or "Resume section"}
Text:
{text}"""
    return _clean_text(await _generate(s, prompt))


async def enhance_project_description(description: str, technologies: str, settings: Settings | None = None) -> str:
    s = settings or get_settings()
    prompt = f"""Improve this project description for a resume (2-3 sentences max).
Highlight scope, technologies, and outcome. Plain text only.

Technologies: {technologies or "Not specified"}
Description:
{description or "Not specified"}"""
    return _clean_text(await _generate(s, prompt))


def _clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    return _strip_code_fences(text)


def _parse_bullet_lines(text: str) -> list[str]:
    if not text:
        return []
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^[-*•]\s*", "", line)
        lines.append(line)
    return lines
