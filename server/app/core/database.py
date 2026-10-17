from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)


def get_session() -> Generator[Session]:
    with Session(engine) as session:
        yield session


def init_db() -> None:
    """Create tables from metadata (prefer Alembic in real deploys)."""
    SQLModel.metadata.create_all(engine)
