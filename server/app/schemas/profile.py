from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ProfileRead(BaseModel):
    id: UUID
    user_id: UUID
    data: dict[str, Any] = Field(default_factory=dict)


class ProfileUpdate(BaseModel):
    data: dict[str, Any]
