"""Versioned HTML/CSS resume templates filled from ResumeDocument JSON.

The LLM never emits HTML — only structured JSON. Preview (Flutter iframe) and
PDF (WeasyPrint) both call ``render_resume_html`` so the DOM stays one SSOT.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.schemas.resume import EducationItem, ResumeDocument, ResumeTemplateInfo

_CERT_MARKERS = (
    "certificat",
    "cert.",
    " certified",
    "license",
    "licence",
    "credential",
    "nanodegree",
    "bootcamp",
)


def education_entry_is_certificate(item: EducationItem | dict[str, object]) -> bool:
    """True when an education row is (or looks like) a certificate / credential."""
    if isinstance(item, EducationItem):
        kind = (item.kind or "").strip().lower()
        blob = f"{item.degree} {item.school}".lower()
    else:
        kind = str(item.get("kind") or "").strip().lower()
        blob = f"{item.get('degree') or ''} {item.get('school') or ''}".lower()
    if kind in {"certificate", "cert", "credential", "license", "licence"}:
        return True
    if kind in {"education", "degree", "school"}:
        return False
    return any(marker in blob for marker in _CERT_MARKERS)


def education_section_title(
    items: list[EducationItem] | list[dict[str, object]],
) -> str:
    """Section heading: include Certificates only when at least one cert is present."""
    if any(education_entry_is_certificate(item) for item in items):
        return "Education & Certificates"
    return "Education"


_TEMPLATES_ROOT = Path(__file__).resolve().parent.parent / "templates" / "resume"

# Registry: template_id → (display name, relative dir under templates/resume, version).
_REGISTRY: dict[str, tuple[str, str, str, str]] = {
    # id → (name, path_under_resume/, version, description)
    "classic": (
        "Classic",
        "classic/v1",
        "v1",
        "Single-column ATS-friendly layout with real text.",
    ),
}


class ResumeTemplateError(Exception):
    def __init__(self, message: str, *, code: str = "template_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


@dataclass(frozen=True, slots=True)
class TemplateSpec:
    id: str
    name: str
    version: str
    description: str
    directory: Path


def list_templates() -> list[ResumeTemplateInfo]:
    return [
        ResumeTemplateInfo(
            id=tid,
            name=meta[0],
            version=meta[2],
            description=meta[3],
        )
        for tid, meta in _REGISTRY.items()
    ]


def get_template(template_id: str) -> TemplateSpec:
    key = (template_id or "classic").strip().lower() or "classic"
    meta = _REGISTRY.get(key)
    if meta is None:
        known = ", ".join(sorted(_REGISTRY))
        raise ResumeTemplateError(
            f"Unknown template_id {template_id!r}. Known: {known}.",
            code="unknown_template",
        )
    name, rel, version, description = meta
    directory = _TEMPLATES_ROOT / rel
    if not (directory / "template.html").is_file():
        raise ResumeTemplateError(
            f"Template assets missing for {key!r}.",
            code="missing_assets",
        )
    return TemplateSpec(
        id=key,
        name=name,
        version=version,
        description=description,
        directory=directory,
    )


@lru_cache(maxsize=8)
def _env_for(directory: str) -> Environment:
    return Environment(
        loader=FileSystemLoader(directory),
        autoescape=select_autoescape(enabled_extensions=("html", "xml")),
    )


def render_resume_html(
    resume: ResumeDocument,
    *,
    template_id: str = "classic",
) -> str:
    """Fill the versioned HTML/CSS template from typed resume JSON."""
    spec = get_template(template_id)
    styles = (spec.directory / "styles.css").read_text(encoding="utf-8")
    env = _env_for(str(spec.directory))
    template = env.get_template("template.html")

    basics = resume.basics
    skills = [
        {"name": g.name, "keywords": g.keywords}
        for g in resume.skills
        if g.name or g.keywords
    ]
    experience = [
        {
            "company": e.company,
            "title": e.title,
            "start": e.start,
            "end": e.end,
            "summary": e.summary,
            "bullets": e.bullets,
        }
        for e in resume.experience
        if e.title or e.company or e.summary or e.bullets
    ]
    projects = [
        {
            "title": p.title,
            "start": p.start,
            "end": p.end,
            "summary": p.summary,
            "bullets": p.bullets,
        }
        for p in resume.projects
        if p.title or p.summary or p.bullets
    ]
    education = [
        {
            "school": e.school,
            "degree": e.degree,
            "end": e.end,
            "kind": e.kind,
        }
        for e in resume.education
        if e.school or e.degree
    ]

    has_content = bool(
        basics.name
        or basics.email
        or basics.phone
        or resume.summary
        or skills
        or experience
        or projects
        or education
    )

    return template.render(
        styles_css=styles,
        basics={
            "name": basics.name,
            "email": basics.email,
            "phone": basics.phone,
            "location": basics.location,
            "citizenship": basics.citizenship,
            "availability": basics.availability,
            "languages": basics.languages,
            "links": basics.links,
        },
        summary=resume.summary,
        skills=skills,
        experience=experience,
        projects=projects,
        education=education,
        education_section_title=education_section_title(
            [e for e in resume.education if e.school or e.degree]
        ),
        has_content=has_content,
    )
