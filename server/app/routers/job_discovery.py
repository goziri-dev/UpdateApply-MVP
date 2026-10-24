"""Match Preferences + Jobs For You APIs (Phase 0 vertical slice)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session

from app.core.auth import DbUser
from app.core.database import get_session
from app.schemas.job_discovery import (
    JobsForYouResponse,
    MatchPreferencesGetResponse,
    MatchPreferencesRead,
    MatchPreferencesUpsert,
    TitleSuggestion,
    TitleSuggestionsResponse,
)
from app.services import match_preferences as prefs_svc
from app.services.title_suggestions import TitleSuggestionError, TitleSuggestionService

router = APIRouter(prefix="/api/v1", tags=["job-discovery"])

SessionDep = Annotated[Session, Depends(get_session)]

# Labeled default until research picks a real daily cap (Phase 2/3).
DEFAULT_SHORTLIST_CAP = 10


def _prefs_read(row: object) -> MatchPreferencesRead:
    data = row.as_public()  # type: ignore[attr-defined]
    return MatchPreferencesRead.model_validate(data)


@router.get(
    "/match-preferences/suggestions",
    response_model=TitleSuggestionsResponse,
)
def suggest_titles(user: DbUser, session: SessionDep) -> TitleSuggestionsResponse:
    try:
        items = TitleSuggestionService().suggest_for_user(session, user.id)
    except TitleSuggestionError as exc:
        status = 404 if exc.code == "missing_profile" else 503
        if exc.code == "suggestions_failed":
            status = 502
        raise HTTPException(
            status_code=status,
            detail={"message": exc.message, "code": exc.code},
        ) from exc
    return TitleSuggestionsResponse(
        suggestions=[TitleSuggestion(**item) for item in items]
    )


@router.get("/match-preferences", response_model=MatchPreferencesGetResponse)
def get_match_preferences(
    user: DbUser,
    session: SessionDep,
) -> MatchPreferencesGetResponse:
    row = prefs_svc.get_for_user(session, user.id)
    if row is None:
        return MatchPreferencesGetResponse(preferences=None)
    return MatchPreferencesGetResponse(preferences=_prefs_read(row))


@router.put("/match-preferences", response_model=MatchPreferencesRead)
def put_match_preferences(
    body: MatchPreferencesUpsert,
    user: DbUser,
    session: SessionDep,
) -> MatchPreferencesRead:
    try:
        row = prefs_svc.replace_for_user(
            session,
            user.id,
            titles=body.titles,
            seniority_bands=list(body.seniority_bands),
            remote_preference=body.remote_preference,
            countries=body.countries,
            city=body.city,
        )
    except prefs_svc.MatchPreferenceError as exc:
        raise HTTPException(
            status_code=400,
            detail={"message": exc.message, "code": exc.code},
        ) from exc
    return _prefs_read(row)


@router.delete(
    "/match-preferences",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_match_preferences(user: DbUser, session: SessionDep) -> Response:
    """Clear saved Job preferences so Jobs For You returns to no_preferences."""
    prefs_svc.delete_for_user(session, user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/jobs-for-you", response_model=JobsForYouResponse)
def jobs_for_you(user: DbUser, session: SessionDep) -> JobsForYouResponse:
    """Ranked shortlist for the signed-in user.

    Phase 0: preferences gate only. Matching / ingest land in Phase 1–2, so
    users with preferences still get an empty list with ``no_matches``.
    """
    row = prefs_svc.get_for_user(session, user.id)
    if row is None or not (row.titles or []):
        return JobsForYouResponse(
            items=[],
            empty_reason="no_preferences",
            cap=DEFAULT_SHORTLIST_CAP,
            cap_is_default=True,
        )

    # Phase 2 will filter + score job_posting rows here.
    return JobsForYouResponse(
        items=[],
        empty_reason="no_matches",
        cap=DEFAULT_SHORTLIST_CAP,
        cap_is_default=True,
    )
