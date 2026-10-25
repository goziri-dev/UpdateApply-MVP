"""Match Preferences + Jobs For You APIs (Phase 0–3)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session

from app.core.auth import DbUser
from app.core.database import get_session
from app.schemas.job_discovery import (
    CareersUrlRequest,
    CareersUrlResponse,
    JobsForYouItem,
    JobsForYouOpenResponse,
    JobsForYouResponse,
    MatchNotificationItem,
    MatchNotificationsResponse,
    MatchPreferencesGetResponse,
    MatchPreferencesRead,
    MatchPreferencesUpsert,
    TitleSuggestion,
    TitleSuggestionsResponse,
)
from app.services import job_match, notify_matches
from app.services import match_preferences as prefs_svc
from app.services.board_detect import BoardDetectError, upsert_board_from_url
from app.services.title_suggestions import TitleSuggestionError, TitleSuggestionService

router = APIRouter(prefix="/api/v1", tags=["job-discovery"])

SessionDep = Annotated[Session, Depends(get_session)]

# Shortlist UI cap — labeled default. Notify uses Settings.notify_daily_cap (Decision).
DEFAULT_SHORTLIST_CAP = job_match.DEFAULT_SHORTLIST_CAP


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
        status_code = 404 if exc.code == "missing_profile" else 503
        if exc.code == "suggestions_failed":
            status_code = 502
        raise HTTPException(
            status_code=status_code,
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
    """Ranked shortlist for the signed-in user (Phase 2).

    Cap stays a labeled default until research chooses a daily number.
    Does not call TailorService or insert applications. Notifications stay off.
    """
    row = prefs_svc.get_for_user(session, user.id)
    if row is None or not (row.titles or []):
        return JobsForYouResponse(
            items=[],
            empty_reason="no_preferences",
            cap=DEFAULT_SHORTLIST_CAP,
            cap_is_default=True,
        )

    hits = job_match.shortlist_for_user(
        session,
        row,
        user_id=user.id,
        cap=DEFAULT_SHORTLIST_CAP,
    )
    if not hits:
        return JobsForYouResponse(
            items=[],
            empty_reason="no_matches",
            cap=DEFAULT_SHORTLIST_CAP,
            cap_is_default=True,
        )

    items = [
        JobsForYouItem(
            posting_id=hit.posting.id,
            title=hit.posting.title or "",
            company=hit.posting.company_name or "",
            location_raw=hit.posting.location_raw or "",
            apply_url=hit.posting.apply_url,
            score=hit.score,
            reason=hit.reason,
            matched_title=hit.matched_title,
            description_text=hit.posting.description_text,
        )
        for hit in hits
    ]
    return JobsForYouResponse(
        items=items,
        empty_reason=None,
        cap=DEFAULT_SHORTLIST_CAP,
        cap_is_default=True,
    )


@router.post(
    "/jobs-for-you/{posting_id}/open",
    response_model=JobsForYouOpenResponse,
)
def open_jobs_for_you_item(
    posting_id: UUID,
    user: DbUser,
    session: SessionDep,
) -> JobsForYouOpenResponse:
    """Mark a shortlist row opened so it is not presented as new next time."""
    ledger = job_match.mark_opened(session, user_id=user.id, posting_id=posting_id)
    if ledger is None or ledger.opened_at is None:
        raise HTTPException(
            status_code=404,
            detail={"message": "Posting not found.", "code": "not_found"},
        )
    return JobsForYouOpenResponse(
        posting_id=posting_id,
        opened_at=ledger.opened_at,
    )


@router.post(
    "/company-boards/from-url",
    response_model=CareersUrlResponse,
)
def add_company_board_from_url(
    body: CareersUrlRequest,
    user: DbUser,
    session: SessionDep,
) -> CareersUrlResponse:
    """Detect vendor/slug from a careers URL and upsert company_board.

    Does not fetch ATS jobs — the next shared ingest picks the board up for
    everyone. Auth is required so anonymous clients cannot spam the catalog;
    the row is still global (no user id on the board).
    """
    _ = user
    try:
        result = upsert_board_from_url(session, body.url)
    except BoardDetectError as exc:
        raise HTTPException(
            status_code=400,
            detail={"message": exc.message, "code": exc.code},
        ) from exc

    board = result.board
    if result.created:
        message = (
            f"Added {board.company_name} ({board.vendor}/{board.slug}) for everyone. "
            "Jobs appear after the next ingest — not instantly."
        )
    elif result.reactivated:
        message = (
            f"Revived {board.company_name} ({board.vendor}/{board.slug}). "
            "Jobs appear after the next ingest — not instantly."
        )
    else:
        message = (
            f"{board.company_name} ({board.vendor}/{board.slug}) is already in the "
            "catalog. Jobs appear after the next ingest — not instantly."
        )
    return CareersUrlResponse(
        vendor=board.vendor,
        slug=board.slug,
        company_name=board.company_name,
        status=board.status,
        source=board.source,
        created=result.created,
        reactivated=result.reactivated,
        message=message,
    )


@router.get(
    "/match-notifications",
    response_model=MatchNotificationsResponse,
)
def get_match_notifications(
    user: DbUser,
    session: SessionDep,
    unread_only: Annotated[bool, Query()] = False,
) -> MatchNotificationsResponse:
    """In-app notification log for strong matches (Phase 3 channel)."""
    items = notify_matches.list_notifications(
        session,
        user.id,
        unread_only=unread_only,
    )
    unread = notify_matches.list_notifications(
        session,
        user.id,
        unread_only=True,
        limit=100,
    )
    return MatchNotificationsResponse(
        items=[
            MatchNotificationItem(
                id=row.id,
                posting_id=row.posting_id,
                title=row.title,
                company=row.company,
                reason=row.reason,
                score=row.score,
                channel=row.channel,
                read_at=row.read_at,
                created_at=row.created_at,
            )
            for row in items
        ],
        unread_count=len(unread),
    )


@router.post(
    "/match-notifications/{notification_id}/read",
    response_model=MatchNotificationItem,
)
def read_match_notification(
    notification_id: UUID,
    user: DbUser,
    session: SessionDep,
) -> MatchNotificationItem:
    row = notify_matches.mark_notification_read(
        session,
        user.id,
        notification_id,
    )
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"message": "Notification not found.", "code": "not_found"},
        )
    return MatchNotificationItem(
        id=row.id,
        posting_id=row.posting_id,
        title=row.title,
        company=row.company,
        reason=row.reason,
        score=row.score,
        channel=row.channel,
        read_at=row.read_at,
        created_at=row.created_at,
    )
