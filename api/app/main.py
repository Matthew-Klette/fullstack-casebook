from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db import make_engine
from app.integrations.payroll import HttpPayrollClient, PayrollClient
from app.migrate import run_migrations
from app.routers import auth, shifts, teams


def create_app(settings: Settings | None = None, payroll: PayrollClient | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.validate()
    engine = make_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if settings.auto_migrate:
            run_migrations(settings.database_url)
        yield
        engine.dispose()

    app = FastAPI(title="Shiftboard API", version="1.0.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = sessionmaker(engine, expire_on_commit=False)
    app.state.payroll = payroll or HttpPayrollClient(
        settings.payroll_url, timeout=settings.payroll_timeout, retries=settings.payroll_retries
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["content-type", "x-requested-with"],
    )
    app.include_router(auth.router)
    app.include_router(teams.router)
    app.include_router(shifts.router)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def app_factory() -> FastAPI:
    """uvicorn --factory entry point."""
    return create_app()
