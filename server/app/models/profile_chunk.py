"""pgvector chunks for remade master-profile RAG (TSK-15)."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

# Must match openai/text-embedding-3-small default dims (and EmbeddingsClient).
EMBEDDING_DIMENSIONS = 1536


class ProfileChunk(SQLModel, table=True):
    """One embeddable slice of a user's approved remade master profile."""

    # SQLModel's default is ``profilechunk``; keep explicit snake_case for SQL.
    # pyrefly: ignore[bad-override]
    __tablename__ = "profile_chunk"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    profile_id: UUID = Field(foreign_key="profile.id", index=True)
    chunk_type: str = Field(index=True, max_length=64)
    source_item_id: str | None = Field(default=None, index=True, max_length=128)
    text: str = Field(sa_column=Column(Text, nullable=False))
    embedding: Any = Field(
        sa_column=Column(Vector(EMBEDDING_DIMENSIONS), nullable=False)
    )
    meta: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSONB, nullable=False, server_default="{}"),
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
