from __future__ import annotations

from pathlib import Path

from alembic.config import Config

from alembic import command

ROOT = Path(__file__).resolve().parent.parent


def run_migrations(database_url: str) -> None:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    cfg.attributes["explicit_url"] = True
    command.upgrade(cfg, "head")
