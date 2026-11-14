from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, Response

from app.deps import DbDep, UserDep, require_csrf_header
from app.models import Membership
from app.schemas import ShiftOut, ShiftUpdate
from app.services import shifts as service

router = APIRouter(prefix="/shifts", tags=["shifts"], dependencies=[Depends(require_csrf_header)])


def _load(db, user, shift_id: int):
    try:
        return service.get_shift_for_user(db, user, shift_id)
    except service.NotFound:
        raise HTTPException(status_code=404, detail="shift not found") from None


@router.get("/{shift_id}", response_model=ShiftOut)
def get_shift(shift_id: int, user: UserDep, db: DbDep) -> ShiftOut:
    return ShiftOut.model_validate(_load(db, user, shift_id))


@router.patch(
    "/{shift_id}",
    response_model=ShiftOut,
    responses={409: {"description": "The shift changed since the supplied version"}},
)
def update_shift(shift_id: int, body: ShiftUpdate, user: UserDep, db: DbDep):
    shift = _load(db, user, shift_id)
    try:
        updated = service.update_shift(db, shift, body)
    except service.InvalidAssignee:
        raise HTTPException(
            status_code=422, detail="assignee is not a member of this team"
        ) from None
    except service.VersionConflict as conflict:
        return JSONResponse(
            status_code=409,
            content={
                "detail": {"code": "version_conflict", "current_version": conflict.current_version}
            },
        )
    return ShiftOut.model_validate(updated)


@router.delete("/{shift_id}", status_code=204)
def delete_shift(shift_id: int, user: UserDep, db: DbDep) -> Response:
    shift = _load(db, user, shift_id)
    role = db.get(Membership, (user.id, shift.team_id))
    if role is None or role.role != "manager":
        raise HTTPException(status_code=403, detail="manager role required")
    service.delete_shift(db, shift)
    return Response(status_code=204)
