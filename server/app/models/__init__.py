"""SQLModel table modules — import here so Alembic sees metadata."""

from app.models.profile import Profile
from app.models.user import User

__all__ = ["Profile", "User"]
