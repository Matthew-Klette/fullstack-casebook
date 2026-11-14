"""Runtime configuration, read from the environment once at startup."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEV_SECRET = "dev-only-secret-change-me-0000000000"


class ConfigError(Exception):
    pass


def _bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///./shiftboard.db"
    secret_key: str = DEV_SECRET
    # Origins allowed to call the API from a browser. Empty means same-origin only.
    cors_origins: tuple[str, ...] = ()
    cookie_samesite: str = "lax"  # lax | strict | none
    cookie_secure: bool = False
    auto_migrate: bool = True
    access_ttl_seconds: int = 900
    refresh_ttl_seconds: int = 60 * 60 * 24 * 14
    payroll_url: str = "http://127.0.0.1:9100"
    payroll_timeout: float = 2.0
    payroll_retries: int = 3

    @classmethod
    def from_env(cls) -> Settings:
        env = os.environ.get
        origins = tuple(
            o.strip() for o in (env("SHIFTBOARD_CORS_ORIGINS") or "").split(",") if o.strip()
        )
        return cls(
            database_url=env("SHIFTBOARD_DATABASE_URL", cls.database_url),
            secret_key=env("SHIFTBOARD_SECRET_KEY", DEV_SECRET),
            cors_origins=origins,
            cookie_samesite=env("SHIFTBOARD_COOKIE_SAMESITE", "lax").lower(),
            cookie_secure=_bool(env("SHIFTBOARD_COOKIE_SECURE"), False),
            auto_migrate=_bool(env("SHIFTBOARD_AUTO_MIGRATE"), True),
            payroll_url=env("SHIFTBOARD_PAYROLL_URL", cls.payroll_url),
            payroll_timeout=float(env("SHIFTBOARD_PAYROLL_TIMEOUT", "2.0")),
            payroll_retries=int(env("SHIFTBOARD_PAYROLL_RETRIES", "3")),
        )

    def validate(self) -> None:
        if self.cookie_samesite not in {"lax", "strict", "none"}:
            raise ConfigError(f"invalid cookie_samesite {self.cookie_samesite!r}")
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ConfigError("SameSite=None cookies are rejected by browsers unless Secure is set")
        if "*" in self.cors_origins:
            raise ConfigError("wildcard CORS origins cannot be combined with credentialed requests")
        if self.cookie_secure and self.secret_key == DEV_SECRET:
            raise ConfigError("refusing to run a secure deployment with the development secret")
