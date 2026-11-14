"""Two people edit the same shift. The second save must not silently overwrite the first."""

import threading

from fastapi.testclient import TestClient

from app.models import Shift
from tests.conftest import CSRF, login


def test_stale_version_is_rejected_and_nothing_is_overwritten(client, world, db):
    shift_id = world["k_shift"].id
    ana = login(client, "ana")
    ben = login(TestClient(client.app, headers=CSRF), "ben")

    first = ana.patch(f"/shifts/{shift_id}", json={"version": 1, "title": "Prep (swap with Ana)"})
    assert first.status_code == 200 and first.json()["version"] == 2

    stale = ben.patch(f"/shifts/{shift_id}", json={"version": 1, "title": "Prep (fryer)"})
    assert stale.status_code == 409
    assert stale.json()["detail"] == {"code": "version_conflict", "current_version": 2}

    db.expire_all()
    row = db.get(Shift, shift_id)
    assert (row.title, row.version) == ("Prep (swap with Ana)", 2)


def test_retrying_with_the_current_version_succeeds(client, world):
    shift_id = world["k_shift"].id
    login(client, "ana")
    client.patch(f"/shifts/{shift_id}", json={"version": 1, "status": "done"})
    r = client.patch(f"/shifts/{shift_id}", json={"version": 2, "status": "open"})
    assert r.status_code == 200 and r.json()["version"] == 3


def test_simultaneous_saves_with_the_same_version_have_exactly_one_winner(client, world):
    shift_id = world["k_shift"].id
    names = ("ana", "ben")
    clients = [login(TestClient(client.app, headers=CSRF), n) for n in names]
    barrier = threading.Barrier(2)
    codes: list[int] = []

    def save(c: TestClient, title: str) -> None:
        barrier.wait()
        codes.append(
            c.patch(f"/shifts/{shift_id}", json={"version": 1, "title": title}).status_code
        )

    threads = [
        threading.Thread(target=save, args=(c, f"by {n}"))
        for c, n in zip(clients, names, strict=True)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(codes) == [200, 409]
