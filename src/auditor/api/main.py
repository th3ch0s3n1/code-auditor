"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI

from .routes import scan as scan_router, reports as reports_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="code-auditor API",
        version="0.1.0",
        description="REST API for triggering scans and retrieving reports.",
        lifespan=lifespan,
    )
    application.include_router(scan_router.router, prefix="/scan", tags=["scan"])
    application.include_router(reports_router.router, prefix="/reports", tags=["reports"])
    return application


app = create_app()
