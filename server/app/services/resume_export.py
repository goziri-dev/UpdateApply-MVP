"""HTML → PDF for resume download.

Choice: **PyMuPDF Story** (not WeasyPrint, not Playwright).

Why this fits the stack:
- ``pymupdf`` is already required for resume *ingest* (upload → text).
- ``Story`` consumes the same Jinja-filled HTML/CSS as the Flutter iframe
  preview — LLM never emits HTML; one template fills both surfaces.
- No Pango/Cairo host packages (WeasyPrint) and no Chromium sidecar
  (Playwright). Pure ``uv`` install stays enough for local + CI.

Letter page + 0.65in margins mirror the classic template ``@page`` intent;
MuPDF lays out the story into that content box.
"""

from __future__ import annotations

import io

import pymupdf

from app.schemas.resume import ResumeDocument
from app.services.resume_render import render_resume_html

# Letter with ~0.65in margins (matches classic/v1 @page intent).
_MEDIABOX = pymupdf.paper_rect("letter")
_MARGIN = 47  # ~0.65in at 72 dpi
_CONTENT = _MEDIABOX + (_MARGIN, _MARGIN, -_MARGIN, -_MARGIN)


class ResumeExportError(Exception):
    def __init__(self, message: str, *, code: str = "export_failed") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def resume_to_pdf_bytes(
    resume: ResumeDocument,
    *,
    template_id: str = "classic",
) -> bytes:
    html = render_resume_html(resume, template_id=template_id)
    try:
        story = pymupdf.Story(html=html)
        buffer = io.BytesIO()
        writer = pymupdf.DocumentWriter(buffer)

        def rectfn(rect_num: int, filled: pymupdf.Rect) -> tuple:
            return _MEDIABOX, _CONTENT, pymupdf.Identity

        story.write(writer, rectfn)
        writer.close()
        pdf = buffer.getvalue()
    except (OSError, RuntimeError, ValueError, TypeError) as exc:
        raise ResumeExportError(
            "PDF export failed while laying out the resume HTML.",
            code="pymupdf_story_failed",
        ) from exc
    if not pdf:
        raise ResumeExportError("PDF export produced empty output.", code="empty_pdf")
    return bytes(pdf)


def download_filename(resume: ResumeDocument) -> str:
    name = (resume.basics.name or "resume").strip()
    slug = "".join(ch if ch.isalnum() else "_" for ch in name).strip("_")
    slug = slug or "resume"
    role = (resume.meta.target_role or "").strip()
    if role:
        role_slug = "".join(ch if ch.isalnum() else "_" for ch in role).strip("_")
        if role_slug:
            return f"{slug}_{role_slug}.pdf"
    return f"{slug}.pdf"
