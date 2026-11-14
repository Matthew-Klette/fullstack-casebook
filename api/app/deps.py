from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import get_db
from app.models import Membership, User
from app.security import decode_access_token

DbDep = Annotated[Session, Depends(get_db)]

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_HEADER = "x-requested-with"
CSRF_VALUE = "shiftboard"


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


SettingsDep = Annotated[Settings, Depends(get_settings)]


def require_csrf_header(request: Request) -> None:
    """Cookies are sent automatically; a custom header forces a CORS preflight."""
    if request.method not in SAFE_METHODS and request.headers.get(CSRF_HEADER) != CSRF_VALUE:
        raise HTTPException(status_code=403, detail="missing X-Requested-With header")


def current_user(request: Request, db: DbDep, settings: SettingsDep) -> User:
    token = request.cookies.get("access_token")
    user_id = decode_access_token(token, settings) if token else None
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    return user


UserDep = Annotated[User, Depends(current_user)]


def team_membership(team_id: int, user: UserDep, db: DbDep) -> Membership:
    """404 for non-members so team ids cannot be enumerated."""
    membership = db.scalar(
        select(Membership).where(Membership.team_id == team_id, Membership.user_id == user.id)
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="team not found")
    return membership


MembershipDep = Annotated[Membership, Depends(team_membership)]


def require_manager(membership: MembershipDep) -> Membership:
    if membership.role != "manager":
        raise HTTPException(status_code=403, detail="manager role required")
    return membership


ManagerDep = Annotated[Membership, Depends(require_manager)]
