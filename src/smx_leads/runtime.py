from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from smx_leads.core.config import LeadsConfig
from smx_leads.models import LeadsBase


@dataclass(frozen=True)
class LeadsRuntime:
    config: LeadsConfig
    engine: Engine
    session_factory: sessionmaker[Session]

    @classmethod
    def from_mapping(cls, values: dict | None) -> "LeadsRuntime":
        config = LeadsConfig.from_mapping(values)
        engine = _create_engine(config.database_url)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)

        return cls(
            config=config,
            engine=engine,
            session_factory=session_factory,
        )

    def init_schema(self) -> None:
        LeadsBase.metadata.create_all(self.engine)

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        session = self.session_factory()

        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def _create_engine(database_url: str) -> Engine:
    if database_url == "sqlite+pysqlite:///:memory:":
        return create_engine(
            database_url,
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    return create_engine(database_url, future=True)
