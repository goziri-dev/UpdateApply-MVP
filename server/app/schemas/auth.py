from pydantic import BaseModel


class AuthProviderInfo(BaseModel):
    provider: str
    authorize_url: str | None = None
    configured: bool
    detail: str


class AuthProvidersResponse(BaseModel):
    providers: list[AuthProviderInfo]


class AuthMeResponse(BaseModel):
    id: str
    email: str | None = None
    role: str | None = None
