from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuthProviderInfo(BaseModel):
    provider: str
    authorize_url: str | None = None
    configured: bool
    detail: str


class AuthProvidersResponse(BaseModel):
    providers: list[AuthProviderInfo]


class AuthMeResponse(BaseModel):
    """Persisted app ``User`` plus JWT role and allowlist status."""

    id: UUID
    email: str | None = None
    display_name: str | None = None
    oauth_provider: str | None = None
    oauth_subject: str
    onboarding_status: str = "not_started"
    role: str | None = None
    # False → Flutter shows private-beta blocked state; API routes return 403.
    allowlisted: bool = False
    created_at: datetime
    updated_at: datetime
