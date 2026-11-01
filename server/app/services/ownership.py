"""Owner-scoped row access helpers.

FastAPI connects via ``DATABASE_URL`` (privileged DB role that bypasses RLS),
so application-layer ``user_id`` checks remain the primary isolation guarantee.
Use these helpers for ID-keyed reads/writes so cross-user access always 404s.
"""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, SQLModel


class OwnershipError(Exception):
    """Raised when a row is missing or not owned by the caller."""

    def __init__(self, message: str = "Not found.", *, code: str = "not_found") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def get_owned[T: SQLModel](
    session: Session,
    model: type[T],
    *,
    row_id: UUID,
    user_id: UUID,
    not_found_message: str = "Not found.",
) -> T:
    """Load ``model`` by primary key and require ``row.user_id == user_id``.

    Missing rows and wrong-owner rows both raise :class:`OwnershipError` with
    ``code="not_found"`` so callers do not leak existence across users.
    """
    row = session.get(model, row_id)
    if row is None:
        raise OwnershipError(not_found_message, code="not_found")
    owner = getattr(row, "user_id", None)
    if owner != user_id:
        raise OwnershipError(not_found_message, code="not_found")
    return row


def require_same_owner(
    *,
    resource_user_id: UUID,
    caller_user_id: UUID,
    message: str = "Not found.",
) -> None:
    """Raise :class:`OwnershipError` when resource owner ≠ caller."""
    if resource_user_id != caller_user_id:
        raise OwnershipError(message, code="not_found")
