from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models.resume import ResumeData

logger = logging.getLogger(__name__)

_env: Environment | None = None


def _get_env() -> Environment:
    global _env
    if _env is None:
        tpl_dir = Path(__file__).resolve().parent.parent / "templates"
        _env = Environment(
            loader=FileSystemLoader(str(tpl_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
    return _env


def render_resume_html(data: ResumeData) -> str:
    env = _get_env()
    tpl = env.get_template("resume_ats.html")
    return tpl.render(resume=data)
