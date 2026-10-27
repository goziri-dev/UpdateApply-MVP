from pydantic import BaseModel, Field


CAREER_STAGES = (
    "student",
    "early_career",
    "mid_career",
    "senior",
    "career_changer",
    "other",
)


class WaitlistSignupRequest(BaseModel):
    email: str = Field(min_length=1, max_length=254)
    name: str = Field(min_length=1, max_length=120)
    career_stage: str = Field(min_length=1, max_length=32)
    job_search_challenges: str | None = Field(default=None, max_length=1000)
    source: str | None = Field(default=None, max_length=64)


class WaitlistSignupResponse(BaseModel):
    status: str = "ok"
    email: str
    duplicate: bool


class WaitlistErrorResponse(BaseModel):
    error: str
    message: str
