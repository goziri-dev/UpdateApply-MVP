"""Regression: user A cannot read/update user B's PII resources."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.models.application import Application
from app.models.profile import Profile
from app.services.applications import ApplicationError, ApplicationService
from app.services.deepen_session import (
    DeepenSession,
    DeepenSessionStore,
    new_session_id,
)
from app.services.edit_session import EditSessionStore
from app.services.ownership import OwnershipError, get_owned, require_same_owner
from app.services.profile_index import ProfileIndexError, ProfileIndexService
from app.services.resume_storage import ResumeStorage, ResumeStorageError


def test_get_owned_rejects_cross_user() -> None:
    owner = uuid4()
    other = uuid4()
    row_id = uuid4()
    row = SimpleNamespace(id=row_id, user_id=owner)
    session = MagicMock()
    session.get.return_value = row

    with pytest.raises(OwnershipError) as exc:
        get_owned(
            session,
            Application,
            row_id=row_id,
            user_id=other,
            not_found_message="Application not found.",
        )
    assert exc.value.code == "not_found"
    session.get.assert_called_once_with(Application, row_id)


def test_get_owned_allows_owner() -> None:
    owner = uuid4()
    row_id = uuid4()
    row = SimpleNamespace(id=row_id, user_id=owner)
    session = MagicMock()
    session.get.return_value = row

    out = get_owned(
        session,
        Application,
        row_id=row_id,
        user_id=owner,
    )
    assert out is row


def test_get_owned_missing_is_not_found() -> None:
    session = MagicMock()
    session.get.return_value = None
    with pytest.raises(OwnershipError) as exc:
        get_owned(session, Application, row_id=uuid4(), user_id=uuid4())
    assert exc.value.code == "not_found"


def test_require_same_owner() -> None:
    a, b = uuid4(), uuid4()
    require_same_owner(resource_user_id=a, caller_user_id=a)
    with pytest.raises(OwnershipError) as exc:
        require_same_owner(resource_user_id=a, caller_user_id=b)
    assert exc.value.code == "not_found"


def test_application_service_get_for_user_blocks_other_user() -> None:
    owner = uuid4()
    other = uuid4()
    app_id = uuid4()
    row = SimpleNamespace(
        id=app_id,
        user_id=owner,
        company="Acme",
        target_role="Eng",
        status="draft",
        version=1,
        job_description="JD",
        resume_document={"basics": {"name": "Owner"}},
        apply_url=None,
        applied_at=None,
        created_at=None,
        updated_at=None,
    )
    session = MagicMock()
    session.get.return_value = row
    svc = ApplicationService()

    with pytest.raises(ApplicationError) as exc:
        svc.get_for_user(session, user_id=other, application_id=app_id)
    assert exc.value.code == "not_found"

    with pytest.raises(ApplicationError) as exc:
        svc.delete(session, user_id=other, application_id=app_id)
    assert exc.value.code == "not_found"
    session.delete.assert_not_called()


def test_application_service_get_detail_owner_ok() -> None:
    owner = uuid4()
    app_id = uuid4()
    now = datetime.now(UTC)
    row = SimpleNamespace(
        id=app_id,
        user_id=owner,
        company="Acme",
        target_role="Eng",
        status="draft",
        version=1,
        job_description="Build things",
        resume_document={
            "basics": {"name": "Owner"},
            "experience": [],
            "education": [],
            "skills": [],
            "projects": [],
        },
        apply_url=None,
        applied_at=None,
        created_at=now,
        updated_at=now,
    )
    session = MagicMock()
    session.get.return_value = row
    detail = ApplicationService().get_detail(
        session, user_id=owner, application_id=app_id
    )
    assert detail.id == app_id
    assert detail.company == "Acme"


def test_edit_session_cross_user_denied() -> None:
    store = EditSessionStore()
    owner = uuid4()
    other = uuid4()
    session = store.get_or_create(user_id=owner, session_id=None)

    assert store.get(user_id=other, session_id=session.session_id) is None
    assert store.delete(user_id=other, session_id=session.session_id) is False
    assert store.get(user_id=owner, session_id=session.session_id) is not None


def test_deepen_session_cross_user_denied() -> None:
    store = DeepenSessionStore()
    owner = uuid4()
    other = uuid4()
    sid = new_session_id()
    store.create(
        DeepenSession(
            session_id=sid,
            user_id=owner,
            section="experience",
            index=0,
            item_id="role-1",
            kind="role",
            resume={"basics": {"name": "Owner"}},
            script={"questions": []},
        )
    )

    assert store.get(user_id=other, session_id=sid) is None
    assert store.delete(user_id=other, session_id=sid) is False
    assert store.get(user_id=owner, session_id=sid) is not None
    assert store.delete(user_id=owner, session_id=sid) is True


def test_resume_storage_paths_stay_under_user_dir(tmp_path: Path) -> None:
    settings = Settings(resume_upload_dir=str(tmp_path / "uploads"))
    storage = ResumeStorage(settings=settings)
    user_a = uuid4()
    user_b = uuid4()

    saved = storage.save(user_a, b"%PDF-1.4 owner", filename="../../evil.pdf")
    assert saved == storage.resume_path(user_a)
    assert saved.is_relative_to(storage.user_dir(user_a))
    assert not saved.is_relative_to(storage.user_dir(user_b))

    meta = storage.user_dir(user_a) / "filename.txt"
    assert meta.read_text(encoding="utf-8") == "evil.pdf"

    assert storage.load(user_b) is None
    assert storage.load(user_a) == b"%PDF-1.4 owner"

    storage.delete(user_a)
    assert storage.load(user_a) is None


def test_resume_storage_sanitize_rejects_dotdot_name() -> None:
    assert ResumeStorage._sanitize_filename("../secret.pdf") == "secret.pdf"
    assert ResumeStorage._sanitize_filename("..") == "resume.pdf"
    assert ResumeStorage._sanitize_filename("") == "resume.pdf"


def test_resume_storage_assert_under_blocks_escape(tmp_path: Path) -> None:
    settings = Settings(resume_upload_dir=str(tmp_path / "uploads"))
    storage = ResumeStorage(settings=settings)
    user_id = uuid4()
    outside = (tmp_path / "outside.pdf").resolve()
    with pytest.raises(ResumeStorageError):
        storage._assert_under(outside, storage.user_dir(user_id), label="test")


def test_profile_reindex_rejects_mismatched_owner() -> None:
    svc = ProfileIndexService.__new__(ProfileIndexService)
    svc.configured = lambda: True  # type: ignore[method-assign]
    owner = uuid4()
    other = uuid4()
    profile = Profile(id=uuid4(), user_id=owner, data={"basics": {"name": "A"}})
    session = MagicMock()

    with pytest.raises(ProfileIndexError) as exc:
        ProfileIndexService.reindex_profile(
            svc, session, user_id=other, profile=profile
        )
    assert exc.value.code == "forbidden_owner"
