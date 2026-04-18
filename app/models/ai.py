from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class SummaryRequest(BaseModel):
    target_role: str = ""
    years_experience: str = ""
    key_skills: str = ""
    highlights: str = ""
    current_summary: str = ""


class BulletsRequest(BaseModel):
    context: str = Field("", description="Job title or project context")
    bullets: list[str] = Field(default_factory=list)


class SkillsSuggestRequest(BaseModel):
    job_role: str = ""
    industry: str = ""
    existing_skills: str = ""


class RephraseRequest(BaseModel):
    text: str = ""
    context: str = ""


class ProjectDescriptionRequest(BaseModel):
    text: str = ""
    technologies: str = ""
    context: str = ""


class AtsScoreRequest(BaseModel):
    target_role: str = ""
    job_description: str = ""
    resume_data: Optional[dict[str, Any]] = None
