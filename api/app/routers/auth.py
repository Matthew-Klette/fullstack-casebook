from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import Settings
from app.deps import DbDep, SettingsDep, UserDep, require_csrf_header
from app.models import Membership, RefreshToken, User
from app.schemas import LoginIn, TeamOut, UserOut
from app.security import (
    hash_refresh_token,
    make_access_token,
    new_refresh_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(require_csrf_header)])

_DUMMY_HASH = "scrypt$" + "00" * 16 + "$" + "00" * 64


def _set_cookie(
    response: Response, settings: Settings, name: str, value: str, max_age: int
) -> None:
    response.set_cookie(
        name,
        value,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,  # type: ignore[arg-type]
        path="/",
    )


def _issue_session(response: Response, db: Session, settings: Settings, user: User) -> None:
    raw, hashed = new_refresh_token()
    expires = datetime.now(UTC) + timedelta(seconds=settings.refresh_ttl_seconds)
    db.add(RefreshToken(user_id=user.id, token_hash=hashed, expires_at=expires))
    db.commit()
    _set_cookie(
        response,
        settings,
        "access_token",
        make_access_token(user.id, settings),
        settings.access_ttl_seconds,
    )
    _set_cookie(response, settings, "refresh_token", raw, settings.refresh_ttl_seconds)


def user_out(db: Session, user: User) -> UserOut:
    rows = db.scalars(select(Membership).where(Membership.user_id == user.id)).all()
    teams = sorted(
        (TeamOut(id=m.team.id, name=m.team.name, role=m.role) for m in rows), key=lambda t: t.id
    )  # type: ignore[arg-type]
    return UserOut(id=user.id, email=user.email, name=user.name, teams=teams)


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, response: Response, db: DbDep, settings: SettingsDep) -> UserOut:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    ok = verify_password(body.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not ok:
        raise HTTPException(status_code=401, detail="invalid credentials")
    _issue_session(response, db, settings, user)
    return user_out(db, user)


@router.post("/refresh", response_model=UserOut)
def refresh(request: Request, response: Response, db: DbDep, settings: SettingsDep) -> UserOut:
    raw = request.cookies.get("refresh_token")
    token = (
        db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw)))
        if raw
        else None
    )
    if token is None:
        raise HTTPException(status_code=401, detail="invalid refresh token")
    if token.revoked:
        # A rotated token was presented again: assume theft and end every session for the user.
        db.execute(
            update(RefreshToken).where(RefreshToken.user_id == token.user_id).values(revoked=True)
        )
        db.commit()
        raise HTTPException(status_code=401, detail="refresh token reuse detected")
    if token.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=401, detail="refresh token expired")
    token.revoked = True
    user = db.get(User, token.user_id)
    assert user is not None
    _issue_session(response, db, settings, user)
    return user_out(db, user)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: DbDep) -> Response:
    raw = request.cookies.get("refresh_token")
    if raw:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == hash_refresh_token(raw))
            .values(revoked=True)
        )
        db.commit()
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    response.status_code = 204
    return response


@router.get("/me", response_model=UserOut)
def me(user: UserDep, db: DbDep) -> UserOut:
    return user_out(db, user)
