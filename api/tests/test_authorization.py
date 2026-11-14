"""Team scoping: every shift route must resolve the shift through the caller's membership."""

import pytest

from tests.conftest import login

ROUTES = [
    ("get", {}),
    ("patch", {"json": {"version": 1, "title": "hijacked"}}),
    ("delete", {}),
]


def test_non_member_cannot_read_a_shift_by_id(client, world):
    login(client, "ben")  # kitchen member, not in front of house
    r = client.get(f"/shifts/{world['f_shift'].id}")
    assert r.status_code == 404
    assert "Opening" not in r.text


@pytest.mark.parametrize(("method", "kwargs"), ROUTES)
def test_non_member_is_rejected_on_every_shift_route(client, world, db, method, kwargs):
    login(client, "ana")  # manages kitchen only
    shift_id = world["f_shift"].id
    r = getattr(client, method)(f"/shifts/{shift_id}", **kwargs)
    assert r.status_code == 404
    db.expire_all()
    from app.models import Shift

    row = db.get(Shift, shift_id)
    assert row is not None and (row.title, row.version) == ("Opening", 1)


def test_unknown_id_and_other_teams_id_are_indistinguishable(client, world):
    login(client, "ana")
    other = client.get(f"/shifts/{world['f_shift'].id}")
    missing = client.get("/shifts/99999")
    assert (other.status_code, other.json()) == (missing.status_code, missing.json())


def test_team_members_still_reach_their_own_shifts(client, world):
    login(client, "ben")
    assert client.get(f"/shifts/{world['k_shift'].id}").json()["title"] == "Prep"


def test_cannot_assign_a_shift_to_someone_outside_the_team(client, world):
    login(client, "ana")
    cara = world["users"]["cara"].id
    r = client.patch(f"/shifts/{world['k_shift'].id}", json={"version": 1, "assignee_id": cara})
    assert r.status_code == 422
