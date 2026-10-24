"""SQLModel table modules — import here so Alembic sees metadata."""

from app.models.application import Application
from app.models.match_preference import MatchPreference
from app.models.profile import Profile
from app.models.profile_chunk import ProfileChunk
from app.models.user import User

__all__ = [
    "Application",
    "MatchPreference",
    "Profile",
    "ProfileChunk",
    "User",
]
