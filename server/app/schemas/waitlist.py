from pydantic import BaseModel, Field


class WaitlistSignupRequest(BaseModel):
    email: str = Field(min_length=1, max_length=254)
    source: str | None = Field(default=None, max_length=64)


class WaitlistSignupResponse(BaseModel):
    status: str = "ok"
    email: str
    duplicate: bool


class WaitlistErrorResponse(BaseModel):
    error: str
    message: str
