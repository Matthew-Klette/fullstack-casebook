from datetime import UTC, datetime

from tests.conftest import login


def test_members_list_only_their_team_shifts(client, world):
    login(client, "ben")
    kitchen = world["kitchen"].id
    r = client.get(f"/teams/{kitchen}/shifts")
    assert [s["title"] for s in r.json()] == ["Prep"]
    assert r.json()[0]["assignee_name"] == "Ben"
    assert client.get(f"/teams/{world['floor'].id}/shifts").status_code == 404


def test_create_shift_and_validate_assignee_membership(client, world):
    login(client, "ana")
    kitchen = world["kitchen"].id
    body = {"title": "Dinner", "starts_at": datetime(2030, 1, 1, 17, tzinfo=UTC).isoformat()}
    created = client.post(f"/teams/{kitchen}/shifts", json=body)
    assert created.status_code == 201
    assert created.json()["version"] == 1 and created.json()["status"] == "open"
    cara = world["users"]["cara"].id
    bad = client.post(f"/teams/{kitchen}/shifts", json={**body, "assignee_id": cara})
    assert bad.status_code == 422


def test_patch_updates_fields_and_bumps_version(client, world):
    login(client, "ben")
    shift = world["k_shift"]
    r = client.patch(f"/shifts/{shift.id}", json={"version": 1, "status": "done"})
    assert r.status_code == 200
    assert (r.json()["status"], r.json()["version"], r.json()["title"]) == ("done", 2, "Prep")


def test_only_managers_delete(client, world):
    shift_id = world["k_shift"].id
    login(client, "ben")
    assert client.delete(f"/shifts/{shift_id}").status_code == 403
    login(client, "ana")
    assert client.delete(f"/shifts/{shift_id}").status_code == 204
    assert client.get(f"/shifts/{shift_id}").status_code == 404
