import os

from sqlalchemy import engine_from_config, pool

from alembic import context
from app import models  # noqa: F401  (registers tables on Base.metadata)
from app.db import Base

config = context.config
target_metadata = Base.metadata


def _url() -> str:
    # The app passes its URL explicitly; the env var only matters for the alembic CLI.
    explicit = config.get_main_option("sqlalchemy.url")
    return (
        explicit
        if config.attributes.get("explicit_url")
        else os.environ.get("SHIFTBOARD_DATABASE_URL", explicit)
    )


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = _url()
    engine = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, render_as_batch=True
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
