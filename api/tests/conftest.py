from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import Base
from app.integrations.payroll import FakePayrollClient
from app.main import create_app
from app.models import Membership, Shift, Team, User
from app.security import hash_password

PASSWORD = "correct horse battery"
CSRF = {"X-Requested-With": "shiftboard"}


def make_settings(tmp_path, **overrides) -> Settings:
    base = {"database_url": f"sqlite:///{tmp_path}/test.db", "auto_migrate": False}
    return Settings(**{**base, **overrides})


def build_client(tmp_path, payroll=None, **overrides) -> TestClient:
    app = create_app(make_settings(tmp_path, **overrides), payroll=payroll or FakePayrollClient())
    Base.metadata.create_all(app.state.engine)
    client = TestClient(app, headers=CSRF)
    return client


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    with build_client(tmp_path) as c:
        yield c


@pytest.fixture
def db(client) -> Iterator[Session]:
    with client.app.state.session_factory() as session:
        yield session


@pytest.fixture
def world(db):
    """Two teams. ana manages kitchen, ben is a kitchen member, cara manages front of house."""
    pw = hash_password(PASSWORD)
    users = {
        name: User(email=f"{name}@example.test", name=name.title(), password_hash=pw)
        for name in ("ana", "ben", "cara")
    }
    kitchen, floor = Team(name="Kitchen"), Team(name="Front of house")
    db.add_all([*users.values(), kitchen, floor])
    db.flush()
    db.add_all(
        [
            Membership(user_id=users["ana"].id, team_id=kitchen.id, role="manager"),
            Membership(user_id=users["ben"].id, team_id=kitchen.id, role="member"),
            Membership(user_id=users["cara"].id, team_id=floor.id, role="manager"),
        ]
    )
    when = datetime.now(UTC) + timedelta(days=1)
    k_shift = Shift(team_id=kitchen.id, title="Prep", starts_at=when, assignee_id=users["ben"].id)
    f_shift = Shift(team_id=floor.id, title="Opening", starts_at=when)
    db.add_all([k_shift, f_shift])
    db.commit()
    return {
        "users": users,
        "kitchen": kitchen,
        "floor": floor,
        "k_shift": k_shift,
        "f_shift": f_shift,
    }


def login(client: TestClient, name: str) -> TestClient:
    r = client.post("/auth/login", json={"email": f"{name}@example.test", "password": PASSWORD})
    assert r.status_code == 200, r.text
    return client
