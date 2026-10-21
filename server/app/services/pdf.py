"""PDF → text helpers for resume extract (pymupdf4llm).

Used by ``ResumeExtractService`` after ``ResumeStorage`` loads uploaded bytes.
"""

from __future__ import annotations

import pymupdf
import pymupdf4llm


def pdf_bytes_to_markdown(
    data: bytes,
    *,
    filename: str = "resume.pdf",
    use_ocr: bool = False,
) -> str:
    """Convert PDF bytes to Markdown suited for LLM context.

    OCR is off by default — text resumes are the common case and layout OCR
    is slower/heavier. Pass ``use_ocr=True`` for scanned PDFs.
    """
    if not data:
        raise ValueError("PDF bytes are empty.")

    doc = pymupdf.open(stream=data, filetype="pdf")
    try:
        markdown = pymupdf4llm.to_markdown(
            doc,
            filename=filename,
            use_ocr=use_ocr,
        )
    finally:
        doc.close()

    return _as_plain_string(markdown)


def pdf_bytes_to_text(
    data: bytes,
    *,
    filename: str = "resume.pdf",
    use_ocr: bool = False,
) -> str:
    """Plain-text extract (tables as text grids). Prefer markdown for LLMs."""
    if not data:
        raise ValueError("PDF bytes are empty.")

    doc = pymupdf.open(stream=data, filetype="pdf")
    try:
        text = pymupdf4llm.to_text(
            doc,
            filename=filename,
            use_ocr=use_ocr,
        )
    finally:
        doc.close()

    return _as_plain_string(text)


def _as_plain_string(value: object) -> str:
    """Normalize pymupdf4llm output (str or page-chunk list) to one string."""
    if isinstance(value, list):
        return "\n\n".join(f"{chunk}" for chunk in value).strip()
    if isinstance(value, str):
        return value.strip()
    return f"{value}".strip()
