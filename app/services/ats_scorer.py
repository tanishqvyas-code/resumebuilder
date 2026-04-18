from __future__ import annotations

import re
from collections import Counter

from app.models.resume import ResumeData

ACTION_VERBS = {
    "achieved",
    "accelerated",
    "analyzed",
    "automated",
    "built",
    "collaborated",
    "created",
    "delivered",
    "designed",
    "developed",
    "drove",
    "enhanced",
    "executed",
    "improved",
    "implemented",
    "increased",
    "launched",
    "led",
    "managed",
    "optimized",
    "owned",
    "reduced",
    "resolved",
    "scaled",
    "streamlined",
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
    "your",
    "you",
}


def score_resume(resume: ResumeData, target_role: str = "", job_description: str = "") -> dict:
    breakdown = []
    strengths: list[str] = []
    concerns: list[str] = []
    suggestions: list[str] = []

    # 1) Section completeness (30)
    personal_fields = [
        resume.personal.full_name,
        resume.personal.email,
        resume.personal.phone,
        resume.personal.location,
        resume.personal.linkedin_url,
        resume.personal.portfolio_url,
    ]
    personal_score = int((sum(1 for x in personal_fields if _has_text(x)) / 6) * 10)
    summary_score = 6 if _has_text(resume.professional_summary) else 0
    skills_score = 4 if any(cat.items for cat in resume.skills) else 0
    work_score = 4 if resume.work_experience else 0
    edu_score = 3 if resume.education else 0
    proj_score = 2 if resume.projects else 0
    lang_score = 1 if resume.languages else 0
    completeness = personal_score + summary_score + skills_score + work_score + edu_score + proj_score + lang_score
    breakdown.append(
        {
            "name": "Section completeness",
            "score": completeness,
            "max": 30,
            "detail": "Checks required ATS sections and contact completeness.",
        }
    )
    if completeness < 24:
        concerns.append("Some key ATS sections are missing or incomplete.")
        suggestions.append("Complete contact details and include summary, skills, work experience, and education.")
    else:
        strengths.append("Core ATS sections are mostly complete.")

    # 2) Keyword alignment (25)
    jd_text = f"{target_role} {job_description}".strip()
    keywords = _extract_keywords(jd_text, limit=24)
    resume_text = _resume_text_blob(resume).lower()
    matches = [k for k in keywords if re.search(rf"\b{re.escape(k)}\b", resume_text)]
    if keywords:
        keyword_score = int((len(matches) / max(len(keywords), 1)) * 25)
    else:
        keyword_score = 0
    breakdown.append(
        {
            "name": "Keyword alignment",
            "score": keyword_score,
            "max": 25,
            "detail": "Compares resume wording against role/job-description keywords.",
            "matched_keywords": matches[:20],
            "missing_keywords": [k for k in keywords if k not in matches][:20],
        }
    )
    if not keywords:
        concerns.append("No job description/target role provided; keyword alignment cannot be scored fairly.")
        suggestions.append("Provide a target role and paste a job description for an honest ATS keyword check.")
    elif keyword_score < 14:
        concerns.append("Low overlap with role-specific keywords.")
        suggestions.append("Add exact role keywords (skills, tools, domain terms) into summary and experience bullets.")
    else:
        strengths.append("Reasonable alignment with role-relevant keywords.")

    # 3) Bullet impact and action verbs (15)
    bullets = [b.strip() for j in resume.work_experience for b in j.bullets if _has_text(b)]
    if not bullets:
        impact_score = 0
    else:
        action_count = 0
        quantified_count = 0
        for b in bullets:
            first = re.sub(r"^[^A-Za-z]*", "", b).split(" ")[0].lower() if b else ""
            if first in ACTION_VERBS:
                action_count += 1
            if re.search(r"(\d+%|\$\d+|\d+\+?|\bmill?ion\b|\bx\b)", b.lower()):
                quantified_count += 1
        action_points = int((action_count / len(bullets)) * 8)
        quantified_points = int((quantified_count / len(bullets)) * 7)
        impact_score = action_points + quantified_points
    breakdown.append(
        {
            "name": "Impact-oriented bullets",
            "score": impact_score,
            "max": 15,
            "detail": "Rewards action verbs and measurable outcomes in experience bullets.",
        }
    )
    if impact_score < 8:
        concerns.append("Experience bullets are weak on action verbs and measurable impact.")
        suggestions.append("Start bullets with strong action verbs and include numbers/results where truthful.")
    else:
        strengths.append("Bullet writing shows action and measurable outcomes.")

    # 4) Clarity and formatting signals (15)
    clarity = 15
    if not re.search(r"[^@\s]+@[^@\s]+\.[^@\s]+", resume.personal.email or ""):
        clarity -= 3
        concerns.append("Email format appears invalid.")
    if len(re.sub(r"\D", "", resume.personal.phone or "")) < 8:
        clarity -= 2
        concerns.append("Phone number looks incomplete.")
    long_bullets = sum(1 for b in bullets if len(b.split()) > 32)
    if long_bullets > 0:
        clarity -= min(5, long_bullets)
        concerns.append("Some bullets are too long and may reduce ATS readability.")
    short_bullets = sum(1 for b in bullets if len(b.split()) < 4)
    if short_bullets > 0:
        clarity -= min(3, short_bullets)
    clarity = max(0, clarity)
    breakdown.append(
        {
            "name": "Clarity and ATS readability",
            "score": clarity,
            "max": 15,
            "detail": "Checks contact validity and bullet clarity/readability.",
        }
    )
    if clarity >= 12:
        strengths.append("Formatting and readability are ATS-friendly.")

    # 5) Content quality balance (15)
    quality = 15
    summary_words = len((resume.professional_summary or "").split())
    if summary_words < 20:
        quality -= 4
        concerns.append("Professional summary is too short for context.")
    elif summary_words > 100:
        quality -= 3
        concerns.append("Professional summary is too long and may dilute impact.")
    if bullets:
        avg_bullet_words = sum(len(b.split()) for b in bullets) / len(bullets)
        if avg_bullet_words < 7 or avg_bullet_words > 28:
            quality -= 4
    if _has_duplicate_lines(bullets):
        quality -= 4
        concerns.append("Duplicate or repetitive bullets detected.")
    quality = max(0, quality)
    breakdown.append(
        {
            "name": "Content quality balance",
            "score": quality,
            "max": 15,
            "detail": "Evaluates concise summary, balanced bullet length, and repetition.",
        }
    )

    total = sum(item["score"] for item in breakdown)
    rating = _rating(total)
    honesty_note = (
        "This ATS score is intentionally conservative and rule-based. "
        "It does not guarantee interview success and does not inflate missing strengths."
    )

    # Deduplicate and keep concise
    strengths = _uniq(strengths)[:6]
    concerns = _uniq(concerns)[:8]
    suggestions = _uniq(suggestions)[:8]

    return {
        "score": total,
        "max_score": 100,
        "rating": rating,
        "honesty_note": honesty_note,
        "breakdown": breakdown,
        "strengths": strengths,
        "concerns": concerns,
        "suggestions": suggestions,
        "input_context": {
            "target_role": target_role,
            "job_description_provided": bool(_has_text(job_description)),
            "bullet_count": len(bullets),
            "keyword_count": len(keywords),
        },
    }


def score_resume_text(text: str, target_role: str = "", job_description: str = "") -> dict:
    """
    Score ATS readiness from raw resume text (e.g., extracted from PDF).
    Conservative by design; avoids inflated scoring.
    """
    raw = (text or "").strip()
    if not raw:
        return {
            "score": 0,
            "max_score": 100,
            "rating": "Needs Work",
            "honesty_note": "No readable text found in uploaded PDF.",
            "breakdown": [
                {"name": "Readable content", "score": 0, "max": 20, "detail": "No extractable text."},
                {"name": "Keyword alignment", "score": 0, "max": 25, "detail": "No extractable text."},
                {"name": "Impact-oriented bullets", "score": 0, "max": 20, "detail": "No extractable text."},
                {"name": "Section coverage", "score": 0, "max": 20, "detail": "No extractable text."},
                {"name": "Clarity signals", "score": 0, "max": 15, "detail": "No extractable text."},
            ],
            "strengths": [],
            "concerns": ["Uploaded PDF does not contain readable text (likely scanned/image PDF)."],
            "suggestions": ["Upload a text-based PDF or run OCR first."],
            "input_context": {"text_chars": 0, "keyword_count": 0},
        }

    lower = raw.lower()
    concerns: list[str] = []
    strengths: list[str] = []
    suggestions: list[str] = []

    # 1) Readable content quality (20)
    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9+\-/#.]*\b", raw)
    unique_ratio = len(set(w.lower() for w in words)) / max(len(words), 1)
    readable_score = 20
    if len(raw) < 800:
        readable_score -= 8
        concerns.append("Resume text appears too short; extraction may be incomplete.")
    if unique_ratio < 0.25:
        readable_score -= 4
        concerns.append("Text has low variety and may contain extraction noise.")
    if re.search(r"(.)\1{5,}", raw):
        readable_score -= 3
    readable_score = max(0, readable_score)

    # 2) Keyword alignment (25)
    jd_text = f"{target_role} {job_description}".strip()
    keywords = _extract_keywords(jd_text, limit=30)
    matches = [k for k in keywords if re.search(rf"\b{re.escape(k)}\b", lower)]
    keyword_score = int((len(matches) / max(len(keywords), 1)) * 25) if keywords else 0
    if not keywords:
        concerns.append("No target role/job description provided; keyword score is limited.")
        suggestions.append("Provide target role and job description for a fair keyword match.")
    elif keyword_score < 14:
        concerns.append("Low overlap with role-specific keywords in the uploaded resume.")
        suggestions.append("Add exact role keywords from the JD into summary, skills, and experience.")
    else:
        strengths.append("Reasonable role keyword alignment.")

    # 3) Bullet impact (20)
    bullet_lines = []
    for line in raw.splitlines():
        t = line.strip()
        if re.match(r"^[-•*]\s+", t):
            bullet_lines.append(re.sub(r"^[-•*]\s+", "", t))
    impact_score = 0
    if bullet_lines:
        action_count = 0
        quantified_count = 0
        for b in bullet_lines:
            first = re.sub(r"^[^A-Za-z]*", "", b).split(" ")[0].lower() if b else ""
            if first in ACTION_VERBS:
                action_count += 1
            if re.search(r"(\d+%|\$\d+|\d+\+?|\bmill?ion\b|\bx\b)", b.lower()):
                quantified_count += 1
        impact_score = int((action_count / len(bullet_lines)) * 10) + int((quantified_count / len(bullet_lines)) * 10)
    if impact_score < 10:
        concerns.append("Bullets are weak on action verbs and quantified outcomes.")
        suggestions.append("Start bullets with action verbs and include measurable impact where truthful.")
    else:
        strengths.append("Bullets show action and impact language.")

    # 4) Section coverage (20)
    section_markers = {
        "summary": ["summary", "professional summary", "profile"],
        "skills": ["skills", "technical skills", "core skills"],
        "experience": ["experience", "professional experience", "work experience"],
        "education": ["education", "academic"],
        "projects": ["projects"],
        "certifications": ["certifications", "certification", "training"],
    }
    covered = 0
    for _, variants in section_markers.items():
        if any(v in lower for v in variants):
            covered += 1
    section_score = int((covered / len(section_markers)) * 20)
    if section_score < 12:
        concerns.append("Important ATS sections appear missing or unclear in the PDF text.")
        suggestions.append("Use standard section headings: Summary, Skills, Work Experience, Education, etc.")
    else:
        strengths.append("Section structure is mostly ATS-compatible.")

    # 5) Clarity signals (15)
    clarity = 15
    if not re.search(r"[^@\s]+@[^@\s]+\.[^@\s]+", raw):
        clarity -= 4
        concerns.append("Email was not clearly detected.")
    phone_detected = bool(re.search(r"(\+?\d[\d\s\-()]{7,}\d)", raw))
    if not phone_detected:
        clarity -= 3
        concerns.append("Phone number was not clearly detected.")
    if len(bullet_lines) == 0:
        clarity -= 3
    clarity = max(0, clarity)

    breakdown = [
        {"name": "Readable content", "score": readable_score, "max": 20, "detail": "Checks extracted text quality and completeness."},
        {
            "name": "Keyword alignment",
            "score": keyword_score,
            "max": 25,
            "detail": "Compares extracted text against target role/JD terms.",
            "matched_keywords": matches[:20],
            "missing_keywords": [k for k in keywords if k not in matches][:20],
        },
        {"name": "Impact-oriented bullets", "score": impact_score, "max": 20, "detail": "Rewards strong action and measurable outcomes."},
        {"name": "Section coverage", "score": section_score, "max": 20, "detail": "Detects standard ATS section headings."},
        {"name": "Clarity signals", "score": clarity, "max": 15, "detail": "Detects core contact signals and basic readability."},
    ]
    total = sum(x["score"] for x in breakdown)

    return {
        "score": total,
        "max_score": 100,
        "rating": _rating(total),
        "honesty_note": (
            "This score is based on extracted PDF text and conservative NLP-style rules. "
            "If extraction is noisy, the score may be lower by design."
        ),
        "breakdown": breakdown,
        "strengths": _uniq(strengths)[:6],
        "concerns": _uniq(concerns)[:8],
        "suggestions": _uniq(suggestions)[:8],
        "input_context": {
            "target_role": target_role,
            "job_description_provided": bool(_has_text(job_description)),
            "text_chars": len(raw),
            "bullet_count": len(bullet_lines),
            "keyword_count": len(keywords),
        },
    }


def _extract_keywords(text: str, limit: int = 24) -> list[str]:
    if not _has_text(text):
        return []
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9\-\+\.#/]{1,}", text.lower())
    tokens = [t.strip(".") for t in tokens if t not in STOPWORDS and len(t) > 2]
    freq = Counter(tokens)
    return [w for w, _ in freq.most_common(limit)]


def _resume_text_blob(resume: ResumeData) -> str:
    pieces: list[str] = []
    pieces.extend(
        [
            resume.personal.full_name,
            resume.personal.location,
            resume.professional_summary,
        ]
    )
    for cat in resume.skills:
        pieces.append(cat.category_name)
        pieces.extend(cat.items)
    for job in resume.work_experience:
        pieces.extend([job.job_title, job.company_name, job.location, " ".join(job.bullets)])
    for ed in resume.education:
        pieces.extend([ed.degree, ed.institution, ed.location, ed.graduation_year or ""])
    for pr in resume.projects:
        pieces.extend([pr.title, pr.description, pr.technologies_used])
    for c in resume.certifications:
        pieces.extend([c.name, c.issuer, c.date])
    pieces.extend(resume.achievements)
    for lang in resume.languages:
        pieces.extend([lang.language, lang.proficiency])
    return " ".join(p for p in pieces if _has_text(p))


def _has_duplicate_lines(lines: list[str]) -> bool:
    norm = [re.sub(r"\s+", " ", l.strip().lower()) for l in lines if _has_text(l)]
    return len(norm) != len(set(norm))


def _rating(score: int) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Strong"
    if score >= 55:
        return "Fair"
    return "Needs Work"


def _has_text(v: str | None) -> bool:
    return bool(v and str(v).strip())


def _uniq(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out
