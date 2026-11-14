from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from app.models import Membership, Shift, User
from app.schemas import ShiftCreate, ShiftUpdate


class NotFound(Exception):
    pass


class VersionConflict(Exception):
    def __init__(self, current_version: int):
        self.current_version = current_version


class InvalidAssignee(Exception):
    pass


def list_shifts(db: Session, team_id: int, status: str | None = None) -> list[Shift]:
    stmt = (
        select(Shift)
        .where(Shift.team_id == team_id)
        .order_by(Shift.starts_at, Shift.id)
    )
    if status:
        stmt = stmt.where(Shift.status == status)
    return list(db.scalars(stmt))


def get_shift_for_user(db: Session, user: User, shift_id: int) -> Shift:
    """Load a shift only if the user belongs to its team. Missing and forbidden look the same."""
    shift = db.scalar(
        select(Shift)
        .join(Membership, Membership.team_id == Shift.team_id)
        .where(Shift.id == shift_id, Membership.user_id == user.id)
        .options(joinedload(Shift.assignee))
    )
    if shift is None:
        raise NotFound
    return shift


def _check_assignee(db: Session, team_id: int, assignee_id: int | None) -> None:
    if assignee_id is None:
        return
    member = db.scalar(
        select(Membership).where(Membership.team_id == team_id, Membership.user_id == assignee_id)
    )
    if member is None:
        raise InvalidAssignee


def create_shift(db: Session, team_id: int, data: ShiftCreate) -> Shift:
    _check_assignee(db, team_id, data.assignee_id)
    shift = Shift(
        team_id=team_id,
        title=data.title,
        notes=data.notes,
        starts_at=data.starts_at,
        assignee_id=data.assignee_id,
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return shift


def update_shift(db: Session, shift: Shift, data: ShiftUpdate) -> Shift:
    fields: dict[str, object] = data.model_dump(
        exclude_unset=True, exclude={"version", "clear_assignee", "assignee_id"}
    )
    if data.clear_assignee:
        fields["assignee_id"] = None
    elif data.assignee_id is not None:
        _check_assignee(db, shift.team_id, data.assignee_id)
        fields["assignee_id"] = data.assignee_id
    # Compare-and-swap: the write only lands if nobody bumped the version since the client read.
    # Doing the comparison inside the UPDATE keeps it atomic; a read-then-check would race.
    result = db.execute(
        update(Shift)
        .where(Shift.id == shift.id, Shift.version == data.version)
        .values(**fields, version=Shift.version + 1)
    )
    if result.rowcount == 0:
        db.rollback()
        current = db.scalar(select(Shift.version).where(Shift.id == shift.id))
        raise VersionConflict(current if current is not None else data.version)
    db.commit()
    db.expire(shift)
    return db.scalar(select(Shift).where(Shift.id == shift.id).options(joinedload(Shift.assignee)))


def delete_shift(db: Session, shift: Shift) -> None:
    db.delete(shift)
    db.commit()


def done_shifts(db: Session, team_id: int) -> list[Shift]:
    return list_shifts(db, team_id, "done")
