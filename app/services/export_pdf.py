from __future__ import annotations

import textwrap
from io import BytesIO

from app.models.resume import ResumeData


def resume_to_pdf_bytes(data: ResumeData) -> bytes:
    # line tuple format:
    # (style, main_text, right_text)
    lines: list[tuple[str, str, str]] = []

    def section(title: str) -> None:
        if title.strip():
            lines.append(("sec", title.strip().upper(), ""))

    def blank() -> None:
        lines.append(("blank", "", ""))

    def normal(text: str) -> None:
        txt = (text or "").strip()
        if txt:
            lines.append(("n", txt, ""))

    def meta(text: str) -> None:
        txt = (text or "").strip()
        if txt:
            lines.append(("m", txt, ""))

    def bullet(text: str) -> None:
        txt = (text or "").strip()
        if txt:
            lines.append(("b", txt, ""))

    def left_right(left: str, right: str, style: str = "lr") -> None:
        l = (left or "").strip()
        r = (right or "").strip()
        if l or r:
            lines.append((style, l, r))

    lines.append(("name", data.personal.full_name or "Your Name", ""))
    headline = _build_headline(data)
    if headline:
        lines.append(("headline", headline, ""))
    contact_parts = _clean_contact_parts(
        [
            data.personal.email,
            data.personal.phone,
            data.personal.location,
            data.personal.linkedin_url,
            data.personal.portfolio_url,
        ]
    )
    if contact_parts:
        left = " | ".join(contact_parts[:3])
        right = " | ".join(contact_parts[3:])
        left_right(left, right, "contact")
    blank()

    if data.professional_summary.strip():
        section("Professional Summary")
        for para in [p.strip() for p in data.professional_summary.split("\n") if p.strip()]:
            normal(para)
        blank()

    if data.skills:
        section("Skills")
        for cat in data.skills:
            if cat.items:
                normal(f"{cat.category_name}: {' | '.join(cat.items)}")
        blank()

    if data.work_experience:
        section("Professional Experience")
        for job in data.work_experience:
            role = " | ".join([x for x in [job.job_title.strip(), job.company_name.strip()] if x])
            dates = " - ".join([x for x in [job.start_date.strip(), job.end_date.strip()] if x])
            left_right(role, dates, "role")
            meta_parts = []
            if job.location.strip():
                meta_parts.append(job.location.strip())
            if meta_parts:
                meta(" | ".join(meta_parts))
            for b in job.bullets:
                bullet(b)
            blank()

    if data.education:
        section("Education")
        for ed in data.education:
            line = " | ".join([x for x in [ed.degree.strip(), ed.institution.strip(), ed.location.strip()] if x])
            if ed.gpa:
                line = f"{line} (GPA: {ed.gpa})" if line else f"GPA: {ed.gpa}"
            left_right(line, ed.graduation_year.strip(), "lr")
        blank()

    if data.projects:
        section("Projects")
        for pr in data.projects:
            left_right(pr.title.strip(), "", "role")
            if pr.technologies_used.strip():
                meta(f"Technologies: {pr.technologies_used.strip()}")
            normal(pr.description)
            meta(pr.link)
            blank()

    if data.certifications:
        section("Certifications and Training")
        for c in data.certifications:
            bullet(" - ".join([x for x in [c.name.strip(), c.issuer.strip(), c.date.strip()] if x]))
        blank()

    if data.achievements:
        section("Achievements")
        for a in data.achievements:
            bullet(a)
        blank()

    if data.languages:
        section("Languages")
        for lang in data.languages:
            bullet(" - ".join([x for x in [lang.language.strip(), lang.proficiency.strip()] if x]))

    return _simple_pdf(lines)


def _clean_contact_parts(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    for v in values:
        txt = (v or "").replace("|", " ").strip()
        txt = " ".join(txt.split())
        if txt:
            cleaned.append(txt)
    return cleaned


def _build_headline(data: ResumeData) -> str:
    """
    Build a concise professional headline under the candidate name.
    """
    if data.work_experience:
        first = data.work_experience[0]
        role = first.job_title.strip()
        if role:
            return role
    summary_line = data.professional_summary.strip().split("\n")[0].strip() if data.professional_summary.strip() else ""
    if summary_line:
        return summary_line[:95].rstrip(".")
    return ""


def _simple_pdf(lines: list[tuple[str, str, str]]) -> bytes:
    page_w = 595  # A4 width
    page_h = 842  # A4 height
    left = 28
    right = 567
    top = 808
    bottom = 30

    def esc(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    
    def text_width(text: str, size: int, bold: bool = False) -> float:
        # Approximate width for Helvetica metrics.
        factor = 0.54 if bold else 0.5
        return len(text) * size * factor

    page_streams: list[bytes] = []
    content_parts: list[str] = []
    y = top

    def start_page() -> None:
        nonlocal content_parts, y
        content_parts = []
        y = top

    def close_page() -> None:
        page_streams.append("\n".join(content_parts).encode("latin-1", errors="ignore"))

    def ensure_space(line_h: int) -> None:
        nonlocal y
        if y - line_h < bottom:
            close_page()
            start_page()

    def draw_text(x: float, yy: float, text: str, size: int, bold: bool = False) -> None:
        font = "F2" if bold else "F1"
        content_parts.append("BT")
        content_parts.append(f"/{font} {size} Tf")
        content_parts.append(f"1 0 0 1 {x:.2f} {yy:.2f} Tm")
        content_parts.append(f"({esc(text)}) Tj")
        content_parts.append("ET")

    def draw_hr(yy: float) -> None:
        content_parts.append(f"{left:.2f} {yy:.2f} m {right:.2f} {yy:.2f} l S")

    def draw_section_bar(y_top: float, height: float = 16) -> None:
        # subtle grey section background like the reference template
        content_parts.append("q")
        content_parts.append("0.90 0.90 0.90 rg")
        content_parts.append(f"{left:.2f} {y_top - height:.2f} {right - left:.2f} {height:.2f} re f")
        content_parts.append("Q")

    def draw_wrapped(text: str, yy: float, size: int, bold: bool, width_chars: int, indent: int = 0, bullet_mode: bool = False) -> float:
        nonlocal y
        chunks = textwrap.wrap(text, width=width_chars) or [text]
        line_h = 15 if size >= 11 else 13
        for idx, c in enumerate(chunks):
            ensure_space(line_h)
            prefix = "- " if bullet_mode and idx == 0 else ("  " if bullet_mode else "")
            draw_text(left + indent, y, f"{prefix}{c}", size, bold)
            y -= line_h
        return y

    def draw_row(left_text: str, right_text: str, size: int, bold: bool, line_h: int, indent: int = 0) -> None:
        nonlocal y
        ensure_space(line_h)
        x_left = left + indent
        draw_text(x_left, y, left_text, size, bold)
        if right_text:
            rw = text_width(right_text, size, bold)
            rx = max(x_left + 220, right - rw)
            draw_text(rx, y, right_text, size, bold)
        y -= line_h

    section_content_indent = 8
    bullet_indent = 20

    start_page()
    for style, raw, right_text in lines:
        if style == "blank":
            ensure_space(8)
            y -= 8
            continue

        plain = raw.replace("\n", " ").strip() if raw else ""
        if not plain:
            if style not in ("contact", "lr", "role"):
                continue

        if style == "name":
            ensure_space(28)
            draw_text(left, y, plain, 30 if len(plain) <= 22 else 27, True)
            y -= 26
            continue

        if style == "headline":
            draw_wrapped(plain, y, 11, False, 88)
            y -= 2
            continue

        if style == "contact":
            draw_row(plain, right_text, 9, False, 13)
            continue

        if style == "sec":
            ensure_space(24)
            draw_section_bar(y + 3, 15)
            draw_text(left + 3, y - 8, plain.title(), 10.5, True)
            y -= 20
            continue

        if style == "role":
            draw_row(plain, right_text, 10.5, True, 15, indent=section_content_indent)
            continue

        if style == "lr":
            draw_row(plain, right_text, 10, False, 13, indent=section_content_indent)
            continue

        if style == "m":
            draw_wrapped(plain, y, 9.5, False, 98, indent=section_content_indent)
            continue

        if style == "b":
            draw_wrapped(plain, y, 9.5, False, 92, indent=bullet_indent, bullet_mode=True)
            continue

        draw_wrapped(plain, y, 9.5, False, 98, indent=section_content_indent)

    close_page()

    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")  # 1
    objects.append(b"<< /Type /Pages /Kids [] /Count 0 >>")  # 2 placeholder
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")  # 3
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")  # 4

    page_obj_ids: list[int] = []
    next_obj_id = 5
    for stream in page_streams:
        page_id = next_obj_id
        content_id = next_obj_id + 1
        page_obj_ids.append(page_id)
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_w} {page_h}] "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_id} 0 R >>"
            ).encode("ascii")
        )
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"\nendstream")
        next_obj_id += 2

    kids = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_obj_ids)} >>".encode("ascii")

    buf = BytesIO()
    buf.write(b"%PDF-1.4\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(buf.tell())
        buf.write(f"{idx} 0 obj\n".encode("ascii"))
        buf.write(obj)
        buf.write(b"\nendobj\n")
    xref_pos = buf.tell()
    buf.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    buf.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        buf.write(f"{off:010d} 00000 n \n".encode("ascii"))
    buf.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode("ascii")
    )
    return buf.getvalue()
