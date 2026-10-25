"""SQLModel table modules — import here so Alembic sees metadata."""

from app.models.application import Application
from app.models.company_board import CompanyBoard
from app.models.job_posting import JobPosting
from app.models.match_ledger import MatchLedger
from app.models.match_notification import MatchNotification
from app.models.match_preference import MatchPreference
from app.models.profile import Profile
from app.models.profile_chunk import ProfileChunk
from app.models.user import User

__all__ = [
    "Application",
    "CompanyBoard",
    "JobPosting",
    "MatchLedger",
    "MatchNotification",
    "MatchPreference",
    "Profile",
    "ProfileChunk",
    "User",
]
