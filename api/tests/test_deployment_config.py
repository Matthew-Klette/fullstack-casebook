"""Settings that only matter once the web app and the API live on different origins."""

import pytest
from fastapi.testclient import TestClient

from app.config import ConfigError, Settings
from app.main import create_app
from tests.conftest import PASSWORD, build_client

WEB = "https://app.example.test"
SPLIT_ORIGIN = {
    "cors_origins": (WEB,),
    "cookie_samesite": "none",
    "cookie_secure": True,
    "secret_key": "x" * 40,
}


def preflight(client: TestClient, origin: str):
    return client.options(
        "/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-requested-with",
        },
    )


def test_preflight_allows_the_configured_web_origin_with_credentials(tmp_path):
    with build_client(tmp_path, **SPLIT_ORIGIN) as client:
        r = preflight(client, WEB)
    assert r.headers["access-control-allow-origin"] == WEB
    assert r.headers["access-control-allow-credentials"] == "true"


def test_preflight_gives_an_unlisted_origin_nothing(tmp_path):
    with build_client(tmp_path, **SPLIT_ORIGIN) as client:
        r = preflight(client, "https://evil.example")
    assert r.status_code == 400  # Starlette refuses the preflight
    assert "access-control-allow-origin" not in r.headers


def test_login_cookies_follow_the_configured_samesite_and_secure_flags(tmp_path, world):
    with build_client(tmp_path, **SPLIT_ORIGIN) as client:
        r = client.post("/auth/login", json={"email": "ana@example.test", "password": PASSWORD})
    cookies = [c.lower() for c in r.headers.get_list("set-cookie")]
    assert len(cookies) == 2
    assert all("samesite=none" in c and "secure" in c for c in cookies), cookies


def test_default_cookies_are_lax_and_not_secure_for_local_development(client, world):
    r = client.post("/auth/login", json={"email": "ana@example.test", "password": PASSWORD})
    cookies = [c.lower() for c in r.headers.get_list("set-cookie")]
    assert all("samesite=lax" in c and "secure" not in c for c in cookies)


@pytest.mark.parametrize(
    "overrides",
    [
        {"cookie_samesite": "none", "cookie_secure": False},
        {"cors_origins": ("*",)},
        {"cookie_secure": True},  # development secret in a secure deployment
        {"cookie_samesite": "sometimes"},
    ],
)
def test_unsafe_combinations_stop_the_app_from_starting(overrides):
    with pytest.raises(ConfigError):
        create_app(Settings(database_url="sqlite://", auto_migrate=False, **overrides))
