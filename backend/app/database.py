from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.models import EnvironmentMetadata


class EnvironmentMismatchError(RuntimeError):
    """Raised when a persistent data plane is mounted under the wrong environment."""


class Database:
    def __init__(self, settings: Settings) -> None:
        self.engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

    @contextmanager
    def session(self) -> Iterator[Session]:
        with self.session_factory() as session:
            yield session

    def dispose(self) -> None:
        self.engine.dispose()


def ensure_environment_identity(database: Database, settings: Settings) -> EnvironmentMetadata:
    with database.session() as db, db.begin():
        metadata = db.scalar(
            select(EnvironmentMetadata)
            .where(EnvironmentMetadata.metadata_id == 1)
            .with_for_update()
        )
        if metadata is None:
            metadata = EnvironmentMetadata(
                metadata_id=1,
                environment=settings.app_environment,
                data_plane_id=uuid4(),
            )
            db.add(metadata)
            db.flush()
        elif metadata.environment != settings.app_environment:
            raise EnvironmentMismatchError(
                "Persistent database identity is "
                f"{metadata.environment!r}, but this API is configured as "
                f"{settings.app_environment!r}. Refusing to start."
            )
        return metadata
