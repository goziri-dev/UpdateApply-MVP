from pydantic import BaseModel


class AuthProviderInfo(BaseModel):
    provider: str
    authorize_url: str | None = None
    configured: bool
    detail: str


class AuthProvidersResponse(BaseModel):
    providers: list[AuthProviderInfo]
