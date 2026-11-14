from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.config import Settings
from app.db import Base, make_engine
from app.main import create_app


def _shape(engine):
    insp = inspect(engine)
    return {
        t: {c["name"]: c["nullable"] for c in insp.get_columns(t)}
        for t in insp.get_table_names()
        if t != "alembic_version"
    }


def test_startup_applies_migrations_and_matches_the_models(tmp_path):
    migrated_url = f"sqlite:///{tmp_path}/migrated.db"
    with TestClient(create_app(Settings(database_url=migrated_url, auto_migrate=True))) as client:
        assert client.get("/health").json() == {"status": "ok"}
    reference = make_engine(f"sqlite:///{tmp_path}/models.db")
    Base.metadata.create_all(reference)
    assert _shape(make_engine(migrated_url)) == _shape(reference)
