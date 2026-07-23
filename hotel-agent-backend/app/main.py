from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.database import close_database_connections
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.modules.identity.routes import router as identity_router

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await close_database_connections()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    description="Backend API for the Agentic Hotel Management System.",
    lifespan=lifespan,
)

app.add_middleware(RequestContextMiddleware)

app.include_router(
    health_router,
)

app.include_router(
    identity_router,
    prefix=settings.api_v1_prefix,
)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "documentation": "/docs",
    }
