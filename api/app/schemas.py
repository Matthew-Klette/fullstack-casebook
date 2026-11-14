from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ShiftStatus = Literal["open", "done"]


class LoginIn(BaseModel):
    email: str
    password: str


class TeamOut(BaseModel):
    id: int
    name: str
    role: Literal["member", "manager"]


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    teams: list[TeamOut]


class MemberOut(BaseModel):
    id: int
    name: str
    role: Literal["member", "manager"]


class ShiftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    title: str
    notes: str
    starts_at: datetime
    status: ShiftStatus
    assignee_id: int | None
    assignee_name: str | None
    version: int


class ShiftCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    notes: str = Field(default="", max_length=2000)
    starts_at: datetime
    assignee_id: int | None = None


class ShiftUpdate(BaseModel):
    """Partial update. `version` is the version the client last saw."""

    version: int
    title: str | None = Field(default=None, min_length=1, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)
    starts_at: datetime | None = None
    status: ShiftStatus | None = None
    assignee_id: int | None = None
    clear_assignee: bool = False


class ExportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    team_id: int
    status: Literal["pending", "sent", "failed"]
    shift_count: int
    remote_ref: str | None
