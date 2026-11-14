from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.deps import (
    DbDep,
    ManagerDep,
    MembershipDep,
    require_csrf_header,
)
from app.models import Membership, User
from app.schemas import ExportOut, MemberOut, ShiftCreate, ShiftOut
from app.services import exports as export_service
from app.services import shifts as shift_service

router = APIRouter(
    prefix="/teams/{team_id}", tags=["teams"], dependencies=[Depends(require_csrf_header)]
)


@router.get("/members", response_model=list[MemberOut])
def members(team_id: int, _m: MembershipDep, db: DbDep) -> list[MemberOut]:
    rows = db.scalars(
        select(Membership).where(Membership.team_id == team_id).options(joinedload(Membership.team))
    ).all()
    users = {
        u.id: u for u in db.scalars(select(User).where(User.id.in_([r.user_id for r in rows])))
    }
    return sorted(
        (MemberOut(id=r.user_id, name=users[r.user_id].name, role=r.role) for r in rows),  # type: ignore[arg-type]
        key=lambda m: m.name,
    )


@router.get("/shifts", response_model=list[ShiftOut])
def list_shifts(
    team_id: int, _m: MembershipDep, db: DbDep, status: str | None = None
) -> list[ShiftOut]:
    return [ShiftOut.model_validate(s) for s in shift_service.list_shifts(db, team_id, status)]


@router.post("/shifts", response_model=ShiftOut, status_code=201)
def create_shift(team_id: int, body: ShiftCreate, _m: MembershipDep, db: DbDep) -> ShiftOut:
    try:
        shift = shift_service.create_shift(db, team_id, body)
    except shift_service.InvalidAssignee:
        raise HTTPException(
            status_code=422, detail="assignee is not a member of this team"
        ) from None
    return ShiftOut.model_validate(shift)


@router.post("/exports", response_model=ExportOut, status_code=201)
def create_export(team_id: int, _m: ManagerDep, db: DbDep, request: Request) -> ExportOut:
    export = export_service.run_export(db, team_id, request.app.state.payroll)
    if export.status == "failed":
        raise HTTPException(
            status_code=502, detail={"code": "payroll_unavailable", "export_id": export.id}
        )
    return ExportOut.model_validate(export)
