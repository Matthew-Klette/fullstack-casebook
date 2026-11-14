from sqlalchemy import select

from app.models import RefreshToken
from tests.conftest import PASSWORD, build_client, login


def test_login_sets_http_only_cookies_and_returns_teams(client, world):
    r = client.post("/auth/login", json={"email": "ana@example.test", "password": PASSWORD})
    assert r.status_code == 200
    assert r.json()["teams"] == [{"id": world["kitchen"].id, "name": "Kitchen", "role": "manager"}]
    cookies = r.headers.get_list("set-cookie")
    assert any(c.startswith("access_token=") and "HttpOnly" in c for c in cookies)
    assert any(c.startswith("refresh_token=") and "HttpOnly" in c for c in cookies)


def test_login_rejects_wrong_password_and_unknown_user(client, world):
    assert (
        client.post(
            "/auth/login", json={"email": "ana@example.test", "password": "nope"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/auth/login", json={"email": "who@example.test", "password": PASSWORD}
        ).status_code
        == 401
    )


def test_unsafe_requests_need_the_csrf_header(tmp_path, world):
    from fastapi.testclient import TestClient

    bare = TestClient(build_client(tmp_path).app)
    r = bare.post("/auth/login", json={"email": "ana@example.test", "password": PASSWORD})
    assert r.status_code == 403


def test_me_requires_a_session(client, world):
    assert client.get("/auth/me").status_code == 401
    login(client, "ben")
    assert client.get("/auth/me").json()["email"] == "ben@example.test"


def test_refresh_rotates_the_token(client, world, db):
    login(client, "ana")
    first = client.cookies.get("refresh_token")
    assert client.post("/auth/refresh").status_code == 200
    assert client.cookies.get("refresh_token") != first
    states = [t.revoked for t in db.scalars(select(RefreshToken).order_by(RefreshToken.id))]
    assert states == [True, False]


def test_reusing_a_rotated_refresh_token_revokes_every_session(client, world, db):
    login(client, "ana")
    stolen = client.cookies.get("refresh_token")
    client.post("/auth/refresh")
    client.cookies.set("refresh_token", stolen)
    assert client.post("/auth/refresh").status_code == 401
    assert all(t.revoked for t in db.scalars(select(RefreshToken)))


def test_logout_revokes_refresh_token_and_clears_cookies(client, world, db):
    login(client, "ana")
    assert client.post("/auth/logout").status_code == 204
    assert client.get("/auth/me").status_code == 401
    assert all(t.revoked for t in db.scalars(select(RefreshToken)))
