from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

from fastapi import Request
from sqlalchemy import DateTime, Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import TypeDecorator


class Base(DeclarativeBase):
    pass


class UTCDateTime(TypeDecorator[datetime]):
    """Stores naive UTC, always returns timezone-aware UTC (SQLite drops tzinfo)."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        return None if value is None else value.replace(tzinfo=UTC)


def make_engine(url: str) -> Engine:
    kwargs: dict = {}
    is_sqlite = url.startswith("sqlite")
    if is_sqlite:
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in {"sqlite://", "sqlite:///:memory:"}:
            kwargs["poolclass"] = StaticPool
    engine = create_engine(url, **kwargs)
    if is_sqlite:

        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _record):
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


def get_db(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session
