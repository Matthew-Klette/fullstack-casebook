"""Query counts, so an N+1 shows up as a failing test instead of a slow page."""

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

from sqlalchemy import event

from app.models import Membership, Shift, User
from tests.conftest import login


@contextmanager
def count_statements(engine):
    statements: list[str] = []

    def record(_conn, _cursor, statement, *_rest):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", record)


def add_assigned_shifts(db, team_id: int, count: int) -> None:
    when = datetime.now(UTC) + timedelta(days=2)
    for i in range(count):
        user = User(email=f"temp{i}@example.test", name=f"Temp {i}", password_hash="x")
        db.add(user)
        db.flush()
        db.add(Membership(user_id=user.id, team_id=team_id, role="member"))
        db.add(Shift(team_id=team_id, title=f"Cover {i}", starts_at=when, assignee_id=user.id))
    db.commit()


def test_listing_shifts_costs_the_same_number_of_queries_for_1_or_25_assignees(client, world, db):
    login(client, "ana")
    url = f"/teams/{world['kitchen'].id}/shifts"
    engine = client.app.state.engine

    with count_statements(engine) as baseline:
        assert client.get(url).status_code == 200
    add_assigned_shifts(db, world["kitchen"].id, 25)
    with count_statements(engine) as grown:
        response = client.get(url)

    assert len(response.json()) == 26
    assert len(grown) == len(baseline), "\n".join(grown)
    assert len(grown) <= 4  # session user, membership, shifts with assignees joined
