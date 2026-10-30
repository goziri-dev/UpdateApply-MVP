"""Contact/header basics: mapping, remake fill, classic template render."""

from app.schemas.resume import ResumeBasics, ResumeDocument
from app.services.resume_basics import basics_from_raw, fill_missing_basics_contact
from app.services.resume_document import (
    profile_to_resume_document,
    resume_document_to_profile_data,
)
from app.services.resume_render import render_resume_html


def test_basics_from_raw_includes_contact_fields() -> None:
    basics = basics_from_raw(
        {
            "name": "Ada Lovelace",
            "email": "ada@example.com",
            "phone": "+353 83 000 0000",
            "location": "Dublin, Ireland",
            "citizenship": "Italian Citizen",
            "availability": "Available full-time",
            "languages": ["English", "Italian"],
            "links": ["linkedin.com/in/ada"],
        }
    )
    assert basics.phone == "+353 83 000 0000"
    assert basics.citizenship == "Italian Citizen"
    assert basics.availability == "Available full-time"
    assert basics.languages == ["English", "Italian"]


def test_fill_missing_basics_contact_restores_empties() -> None:
    remade = {"name": "Ada", "email": "ada@example.com", "location": "Dublin"}
    parsed = {
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "phone": "+353 83 000 0000",
        "location": "Dublin, Ireland",
        "citizenship": "Italian Citizen",
        "availability": "Available full-time",
        "languages": ["English", "Italian"],
    }
    filled = fill_missing_basics_contact(remade, parsed)
    assert filled.phone == "+353 83 000 0000"
    assert filled.citizenship == "Italian Citizen"
    assert filled.availability == "Available full-time"
    assert filled.languages == ["English", "Italian"]
    # Prefer non-empty remade values.
    assert filled.name == "Ada"
    assert filled.location == "Dublin"


def test_profile_roundtrip_preserves_contact() -> None:
    profile = {
        "basics": {
            "name": "Ada",
            "email": "ada@example.com",
            "phone": "+1 555 0100",
            "location": "NYC",
            "citizenship": "US citizen",
            "availability": "Available immediately",
            "languages": ["English"],
            "links": [],
        },
        "summary": "",
        "skills": [],
        "experience": [],
        "education": [],
        "projects": [],
    }
    doc = profile_to_resume_document(profile)
    assert doc.basics.phone == "+1 555 0100"
    assert doc.basics.citizenship == "US citizen"
    back = resume_document_to_profile_data(doc)
    assert back["basics"]["phone"] == "+1 555 0100"
    assert back["basics"]["citizenship"] == "US citizen"
    assert back["basics"]["languages"] == ["English"]


def test_classic_template_renders_phone_and_citizenship() -> None:
    html = render_resume_html(
        ResumeDocument(
            basics=ResumeBasics(
                name="Ada Lovelace",
                email="ada@example.com",
                phone="+353 83 357 6161",
                location="Dublin, Ireland",
                citizenship="Italian Citizen",
                availability="Available full-time",
                languages=["English", "Italian"],
            ),
            summary="Builder.",
        )
    )
    assert "+353 83 357 6161" in html
    assert "Italian Citizen in Dublin, Ireland" in html
    assert "Languages: English, Italian" in html
    assert "Available full-time" in html
    assert "ada@example.com" in html
