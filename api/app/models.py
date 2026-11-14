from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, UTCDateTime


def _now() -> datetime:
    return datetime.now(UTC)


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))


class Membership(Base):
    __tablename__ = "memberships"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), default="member")  # member | manager

    team: Mapped[Team] = relationship()


class Shift(Base):
    __tablename__ = "shifts"
    __table_args__ = (Index("ix_shifts_team_starts", "team_id", "starts_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    title: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str] = mapped_column(String(2000), default="")
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | done
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)

    assignee: Mapped[User | None] = relationship()

    @property
    def assignee_name(self) -> str | None:
        return self.assignee.name if self.assignee else None


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class PayrollExport(Base):
    __tablename__ = "payroll_exports"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | sent | failed
    shift_count: Mapped[int] = mapped_column(Integer, default=0)
    remote_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)
