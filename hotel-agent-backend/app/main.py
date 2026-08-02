from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.database import close_database_connections
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.modules.identity.routes import router as identity_router
from app.modules.knowledge.routes import router as knowledge_router
from app.modules.onboarding.routes import router as onboarding_router

settings = get_settings()

configure_logging(
    settings.log_level,
)


@asynccontextmanager
async def lifespan(
    _: FastAPI,
) -> AsyncIterator[None]:
    """
    Manage application startup and shutdown resources.

    Database connections are created lazily when requests use them. During
    shutdown, the SQLAlchemy connection pool is closed cleanly.
    """

    yield

    await close_database_connections()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    description="Backend API for the Agentic Hotel Management System.",
    lifespan=lifespan,
)

app.add_middleware(
    RequestContextMiddleware,
)

# Health routes already contain their own route prefix.
app.include_router(
    health_router,
)

# Authenticated API routes are grouped below /api/v1.
app.include_router(
    identity_router,
    prefix=settings.api_v1_prefix,
)

app.include_router(
    onboarding_router,
    prefix=settings.api_v1_prefix,
)

app.include_router(
    knowledge_router,
    prefix=settings.api_v1_prefix,
)


@app.get(
    "/",
    tags=["Root"],
)
async def root() -> dict[str, str]:
    """Return basic service information."""

    return {
        "service": settings.app_name,
        "documentation": "/docs",
    }
