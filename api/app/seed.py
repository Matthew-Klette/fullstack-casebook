"""Demo data: `python -m app.seed`. Safe to run twice; it only seeds an empty database."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import make_engine
from app.migrate import run_migrations
from app.models import Membership, Shift, Team, User
from app.security import hash_password

DEMO_PASSWORD = "shiftboard-demo"


def seed(session: Session) -> None:
    if session.scalar(select(User.id).limit(1)) is not None:
        return
    pw = hash_password(DEMO_PASSWORD)
    ana = User(email="ana@example.test", name="Ana Mokoena", password_hash=pw)
    ben = User(email="ben@example.test", name="Ben Naidoo", password_hash=pw)
    cara = User(email="cara@example.test", name="Cara Jacobs", password_hash=pw)
    kitchen = Team(name="Kitchen")
    floor = Team(name="Front of house")
    session.add_all([ana, ben, cara, kitchen, floor])
    session.flush()
    session.add_all(
        [
            Membership(user_id=ana.id, team_id=kitchen.id, role="manager"),
            Membership(user_id=ben.id, team_id=kitchen.id, role="member"),
            Membership(user_id=cara.id, team_id=floor.id, role="manager"),
        ]
    )
    base = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) + timedelta(days=1)
    rows = [
        (kitchen, "Prep: sauces and stocks", ana, 0, "open"),
        (kitchen, "Lunch service, grill", ben, 5, "open"),
        (kitchen, "Deliveries and stock count", None, 8, "open"),
        (kitchen, "Closing clean-down", ben, 12, "done"),
        (floor, "Opening, front of house", cara, 1, "open"),
        (floor, "Weekend brunch cover", None, 30, "open"),
    ]
    for team, title, who, hours, status in rows:
        session.add(
            Shift(
                team_id=team.id,
                title=title,
                starts_at=base + timedelta(hours=hours),
                assignee_id=who.id if who else None,
                status=status,
            )
        )
    session.commit()


if __name__ == "__main__":
    settings = Settings.from_env()
    run_migrations(settings.database_url)
    engine = make_engine(settings.database_url)
    with Session(engine) as s:
        seed(s)
    print(f"seeded {settings.database_url}; demo login ana@example.test / {DEMO_PASSWORD}")
