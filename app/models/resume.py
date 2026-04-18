from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, validator


class PersonalInformation(BaseModel):
    full_name: str = ""
    phone: str = ""
    email: str = ""
    linkedin_url: str = ""
    portfolio_url: str = ""
    location: str = ""

    @validator("linkedin_url", "portfolio_url", pre=True)
    def empty_str(cls, v: object) -> object:
        if v is None:
            return ""
        return v


class SkillCategory(BaseModel):
    category_name: str = Field(..., description='e.g. "Technical Skills"')
    items: list[str] = Field(default_factory=list)


class WorkExperienceItem(BaseModel):
    job_title: str = ""
    company_name: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    bullets: list[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    degree: str = ""
    institution: str = ""
    location: str = ""
    graduation_year: str = ""
    gpa: Optional[str] = None


class ProjectItem(BaseModel):
    title: str = ""
    description: str = ""
    technologies_used: str = ""
    link: str = ""


class CertificationItem(BaseModel):
    name: str = ""
    issuer: str = ""
    date: str = ""


class LanguageItem(BaseModel):
    language: str = ""
    proficiency: str = ""


class ResumeData(BaseModel):
    personal: PersonalInformation = Field(default_factory=PersonalInformation)
    professional_summary: str = ""
    skills: list[SkillCategory] = Field(default_factory=list)
    work_experience: list[WorkExperienceItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    certifications: list[CertificationItem] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    languages: list[LanguageItem] = Field(default_factory=list)

    class Config:
        extra = "ignore"


class ResumeEnvelope(BaseModel):
    """Stored document with metadata for drafts."""

    version: int = 1
    resume: ResumeData = Field(default_factory=ResumeData)
    updated_at: Optional[str] = None
