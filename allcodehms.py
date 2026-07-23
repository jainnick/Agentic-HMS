Directory structure:
└── Agentic-HMS/
    ├── README.md
    ├── requirements.txt
    └── hotel-agent-backend
        ├── .gitignore
        ├── alembic.ini
        ├── APPLY_AND_VALIDATE.md
        ├── pyproject.toml
        ├── README.md
        ├── .github
        │   └── workflows
        │       └── backend-ci.yml
        ├── app
        │   ├── __init__.py
        │   ├── main.py
        │   ├── api
        │   │   ├── __init__.py
        │   │   ├── dependencies.py
        │   │   └── health.py
        │   ├── core
        │   │   ├── __init__.py
        │   │   ├── config.py
        │   │   ├── database.py
        │   │   ├── exceptions.py
        │   │   ├── logging.py
        │   │   ├── middleware.py
        │   │   └── security.py
        │   ├── db
        │   │   ├── __init__.py
        │   │   ├── base.py
        │   │   └── models.py
        │   └── modules
        │       ├── __init__.py
        │       ├── identity
        │       │   ├── __init__.py
        │       │   ├── routes.py
        │       │   ├── schemas.py
        │       │   └── service.py
        │       └── tenancy
        │           ├── __init__.py
        │           ├── enums.py
        │           └── models.py
        ├── migrations
        │   ├── env.py
        │   └── versions
        │       ├── cdff641a8945_initialize_backend_foundation.py
        │       └── f97cc2fbe621_create_tenancy_tables.py
        └── tests
            ├── __init__.py
            ├── conftest.py
            ├── integration
            │   ├── conftest.py
            │   ├── test_database_health.py
            │   └── test_tenancy_models.py
            └── unit
                ├── test_auth_dependencies.py
                └── test_health.py

Generated at: 2026-07-23 18:32:39
Total files included: 41

================================================
FILE: hotel-agent-backend/.github/workflows/backend-ci.yml
================================================
name: Backend CI

on:
  push:
    branches:
      - main
      - develop
      - "feature/**"
  pull_request:

jobs:
  backend-quality:
    runs-on: ubuntu-latest

    defaults:
      run:
        working-directory: hotel-agent-backend

    env:
      DATABASE_URL: postgresql://postgres:postgres@localhost:5432/postgres

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: python -m pip install -e ".[dev]"

      - name: Check formatting
        run: python -m ruff format --check .

      - name: Run linting
        run: python -m ruff check .

      - name: Run type checking
        run: python -m mypy app

      - name: Run unit tests
        run: >
          python -m pytest tests/unit
          --cov=app
          --cov-report=term-missing
          --cov-fail-under=80

================================================
FILE: hotel-agent-backend/.gitignore
================================================
# Secrets
.env
.env.*
!.env.example

# Virtual environments
.venv/
venv/

# Python
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Coverage
.coverage
htmlcov/
*.egg-info/

# IDE
.vscode/
.idea/

================================================
FILE: hotel-agent-backend/alembic.ini
================================================
# A generic, single database configuration.

[alembic]
# path to migration scripts.
# this is typically a path given in POSIX (e.g. forward slashes)
# format, relative to the token %(here)s which refers to the location of this
# ini file
script_location = %(here)s/migrations

# template used to generate migration file names; The default value is %%(rev)s_%%(slug)s
# Uncomment the line below if you want the files to be prepended with date and time
# see https://alembic.sqlalchemy.org/en/latest/tutorial.html#editing-the-ini-file
# for all available tokens
# file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d-%%(rev)s_%%(slug)s
# Or organize into date-based subdirectories (requires recursive_version_locations = true)
# file_template = %%(year)d/%%(month).2d/%%(day).2d_%%(hour).2d%%(minute).2d_%%(second).2d_%%(rev)s_%%(slug)s

# sys.path path, will be prepended to sys.path if present.
# defaults to the current working directory.  for multiple paths, the path separator
# is defined by "path_separator" below.
prepend_sys_path = .

# timezone to use when rendering the date within the migration file
# as well as the filename.
# If specified, requires the tzdata library which can be installed by adding
# `alembic[tz]` to the pip requirements.
# string value is passed to ZoneInfo()
# leave blank for localtime
# timezone =

# max length of characters to apply to the "slug" field
# truncate_slug_length = 40

# set to 'true' to run the environment during
# the 'revision' command, regardless of autogenerate
# revision_environment = false

# set to 'true' to allow .pyc and .pyo files without
# a source .py file to be detected as revisions in the
# versions/ directory
# sourceless = false

# version location specification; This defaults
# to <script_location>/versions.  When using multiple version
# directories, initial revisions must be specified with --version-path.
# The path separator used here should be the separator specified by "path_separator"
# below.
# version_locations = %(here)s/bar:%(here)s/bat:%(here)s/alembic/versions

# path_separator; This indicates what character is used to split lists of file
# paths, including version_locations and prepend_sys_path within configparser
# files such as alembic.ini.
# The default rendered in new alembic.ini files is "os", which uses os.pathsep
# to provide os-dependent path splitting.
#
# Note that in order to support legacy alembic.ini files, this default does NOT
# take place if path_separator is not present in alembic.ini.  If this
# option is omitted entirely, fallback logic is as follows:
#
# 1. Parsing of the version_locations option falls back to using the legacy
#    "version_path_separator" key, which if absent then falls back to the legacy
#    behavior of splitting on spaces and/or commas.
# 2. Parsing of the prepend_sys_path option falls back to the legacy
#    behavior of splitting on spaces, commas, or colons.
#
# Valid values for path_separator are:
#
# path_separator = :
# path_separator = ;
# path_separator = space
# path_separator = newline
#
# Use os.pathsep. Default configuration used for new projects.
path_separator = os


# set to 'true' to search source files recursively
# in each "version_locations" directory
# new in Alembic version 1.10
# recursive_version_locations = false

# the output encoding used when revision files
# are written from script.py.mako
# output_encoding = utf-8

# database URL.  This is consumed by the user-maintained env.py script only.
# other means of configuring database URLs may be customized within the env.py
# file.
sqlalchemy.url = driver://user:pass@localhost/dbname


[post_write_hooks]
# post_write_hooks defines scripts or Python functions that are run
# on newly generated revision scripts.  See the documentation for further
# detail and examples

# format using "black" - use the console_scripts runner, against the "black" entrypoint
# hooks = black
# black.type = console_scripts
# black.entrypoint = black
# black.options = -l 79 REVISION_SCRIPT_FILENAME

# lint with attempts to fix using "ruff" - use the module runner, against the "ruff" module
# hooks = ruff
# ruff.type = module
# ruff.module = ruff
# ruff.options = check --fix REVISION_SCRIPT_FILENAME

# Alternatively, use the exec runner to execute a binary found on your PATH
# hooks = ruff
# ruff.type = exec
# ruff.executable = ruff
# ruff.options = check --fix REVISION_SCRIPT_FILENAME

# Logging configuration.  This is also consumed by the user-maintained
# env.py script only.
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console
qualname =

[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S

================================================
FILE: hotel-agent-backend/app/__init__.py
================================================


================================================
FILE: hotel-agent-backend/app/api/__init__.py
================================================


================================================
FILE: hotel-agent-backend/app/api/dependencies.py
================================================
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from app.core.security import (
    AuthConfigurationError,
    TokenValidationError,
    decode_access_token,
)
from app.modules.identity.schemas import CurrentUser
from app.modules.identity.service import (
    InvalidIdentityClaimsError,
    create_current_user,
)

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="Supabase access token",
)


def authentication_required_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


def invalid_token_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token.",
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> CurrentUser:
    """Validate a Bearer token and return the authenticated user."""

    if credentials is None:
        raise authentication_required_error()

    if credentials.scheme.lower() != "bearer":
        raise authentication_required_error()

    try:
        claims = await decode_access_token(
            credentials.credentials,
        )

        return create_current_user(claims)

    except AuthConfigurationError as exc:
        # This is a server configuration problem, not a user authentication
        # failure, so return 503 instead of 401.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is not configured.",
        ) from exc

    except (
        TokenValidationError,
        InvalidIdentityClaimsError,
    ) as exc:
        raise invalid_token_error() from exc


CurrentUserDependency = Annotated[
    CurrentUser,
    Depends(get_current_user),
]

================================================
FILE: hotel-agent-backend/app/api/health.py
================================================
import asyncio
import logging

from fastapi import APIRouter, HTTPException, status

from app.core.database import check_database_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live")
async def liveness() -> dict[str, str]:
    return {
        "status": "alive",
        "service": "hotel-agent-backend",
    }


@router.get("/ready")
async def readiness() -> dict[str, str]:
    try:
        connected = await asyncio.wait_for(
            check_database_connection(),
            timeout=15,
        )

    except TimeoutError as exc:
        logger.exception("Database readiness check timed out")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service dependency timed out.",
        ) from exc

    except Exception as exc:
        logger.exception("Database readiness check failed")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is not ready.",
        ) from exc

    if connected is not True:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is not ready.",
        )

    return {
        "status": "ready",
        "database": "supabase-postgres",
    }

================================================
FILE: hotel-agent-backend/app/core/__init__.py
================================================


================================================
FILE: hotel-agent-backend/app/core/config.py
================================================
from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "Agentic Hotel Management API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"

    database_url: str
    database_pool_size: int = 5
    database_max_overflow: int = 5
    database_timeout_seconds: int = 10
    database_ssl_mode: str = "require"

    sql_echo: bool = False

    # Supabase project configuration.
    #
    # These remain optional while authentication is being introduced so that
    # existing health checks and unit tests can still start without Supabase
    # Auth configuration. Protected routes will return 503 when they are absent.
    supabase_url: str | None = None
    supabase_anon_key: SecretStr | None = None
    supabase_service_role_key: SecretStr | None = None

    # Supabase user access tokens normally use "authenticated".
    supabase_jwt_audience: str = "authenticated"

    # These can be derived from SUPABASE_URL, but may be overridden.
    supabase_jwt_issuer: str | None = None
    supabase_jwks_url: str | None = None

    # Small allowance for clock differences between systems.
    supabase_jwt_leeway_seconds: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

================================================
FILE: hotel-agent-backend/app/core/database.py
================================================
from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

settings = get_settings()

database_url = make_url(settings.database_url).set(
    drivername="postgresql+asyncpg",
)

engine = create_async_engine(
    database_url,
    echo=settings.sql_echo,
    pool_pre_ping=True,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    connect_args={
        "ssl": settings.database_ssl_mode,
        "timeout": settings.database_timeout_seconds,
    },
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def check_database_connection() -> bool:
    async with engine.connect() as connection:
        value = await connection.scalar(text("SELECT 1"))

    if value != 1:
        raise RuntimeError(f"Unexpected database health-check value: {value!r}")

    return True


async def close_database_connections() -> None:
    await engine.dispose()

================================================
FILE: hotel-agent-backend/app/core/exceptions.py
================================================
from typing import Any


class AppError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}

================================================
FILE: hotel-agent-backend/app/core/logging.py
================================================
import logging
import sys

import structlog


def configure_logging(log_level: str) -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level.upper(),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level.upper()),
        ),
        cache_logger_on_first_use=True,
    )

================================================
FILE: hotel-agent-backend/app/core/middleware.py
================================================
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

RequestHandler = Callable[[Request], Awaitable[Response]]


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestHandler,
    ) -> Response:
        request_id = request.headers.get(
            "X-Request-ID",
            str(uuid.uuid4()),
        )

        request.state.request_id = request_id
        started_at = time.perf_counter()

        response = await call_next(request)

        duration_ms = round(
            (time.perf_counter() - started_at) * 1000,
            2,
        )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(duration_ms)

        return response

================================================
FILE: hotel-agent-backend/app/core/security.py
================================================
import asyncio
from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientError

from app.core.config import Settings, get_settings

# Only asymmetric algorithms supported by this backend are allowed.
#
# Do not derive this list from the incoming JWT header.
ALLOWED_JWT_ALGORITHMS = ["ES256", "RS256"]


class AuthConfigurationError(RuntimeError):
    """Raised when required authentication settings are missing."""


class TokenValidationError(ValueError):
    """Raised when a supplied access token cannot be trusted."""


def resolve_auth_configuration(
    settings: Settings,
) -> tuple[str, str, str, int]:
    """Resolve audience, issuer, JWKS URL, and clock leeway."""

    supabase_url = (settings.supabase_url or "").strip().rstrip("/")

    if not supabase_url:
        raise AuthConfigurationError(
            "SUPABASE_URL is not configured.",
        )

    audience = settings.supabase_jwt_audience.strip()

    if not audience:
        raise AuthConfigurationError(
            "SUPABASE_JWT_AUDIENCE is not configured.",
        )

    issuer = (
        settings.supabase_jwt_issuer.strip().rstrip("/")
        if settings.supabase_jwt_issuer
        else f"{supabase_url}/auth/v1"
    )

    jwks_url = (
        settings.supabase_jwks_url.strip()
        if settings.supabase_jwks_url
        else f"{issuer}/.well-known/jwks.json"
    )

    return (
        audience,
        issuer,
        jwks_url,
        settings.supabase_jwt_leeway_seconds,
    )


@lru_cache(maxsize=4)
def get_jwks_client(
    jwks_url: str,
) -> PyJWKClient:
    """Create and cache a JWKS client for a Supabase project."""

    return PyJWKClient(
        jwks_url,
        cache_keys=True,
    )


def decode_access_token_sync(
    token: str,
) -> dict[str, Any]:
    """Synchronously verify a Supabase access token."""

    if not token.strip():
        raise TokenValidationError(
            "Access token is empty.",
        )

    settings = get_settings()

    audience, issuer, jwks_url, leeway = resolve_auth_configuration(
        settings,
    )

    try:
        jwks_client = get_jwks_client(jwks_url)

        # PyJWT reads the JWT header, obtains the key ID (kid), downloads the
        # matching public key from Supabase JWKS, and returns that signing key.
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        claims = jwt.decode(
            jwt=token,
            key=signing_key.key,
            algorithms=ALLOWED_JWT_ALGORITHMS,
            audience=audience,
            issuer=issuer,
            leeway=leeway,
            options={
                "require": [
                    "exp",
                    "iss",
                    "aud",
                    "sub",
                ],
            },
        )

    except (InvalidTokenError, PyJWKClientError) as exc:
        raise TokenValidationError(
            "Access token is invalid or expired.",
        ) from exc

    if not isinstance(claims, dict):
        raise TokenValidationError(
            "Access token claims are invalid.",
        )

    return claims


async def decode_access_token(
    token: str,
) -> dict[str, Any]:
    """Verify a Supabase access token without blocking FastAPI's event loop."""

    return await asyncio.to_thread(
        decode_access_token_sync,
        token,
    )

================================================
FILE: hotel-agent-backend/app/db/__init__.py
================================================


================================================
FILE: hotel-agent-backend/app/db/base.py
================================================
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class inherited by all database models."""

    pass

================================================
FILE: hotel-agent-backend/app/db/models.py
================================================
from app.db.base import Base
from app.modules.tenancy.models import (
    Organization,
    OrganizationMembership,
    Property,
    PropertyMembership,
)

__all__ = [
    "Base",
    "Organization",
    "OrganizationMembership",
    "Property",
    "PropertyMembership",
]

================================================
FILE: hotel-agent-backend/app/main.py
================================================
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

app.include_router(
    health_router,
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

================================================
FILE: hotel-agent-backend/app/modules/__init__.py
================================================


================================================
FILE: hotel-agent-backend/app/modules/identity/__init__.py
================================================


================================================
FILE: hotel-agent-backend/app/modules/identity/routes.py
================================================
from fastapi import APIRouter

from app.api.dependencies import CurrentUserDependency
from app.modules.identity.schemas import CurrentUser

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.get(
    "/me",
    response_model=CurrentUser,
)
async def get_authenticated_user(
    current_user: CurrentUserDependency,
) -> CurrentUser:
    """Return the authenticated Supabase user's identity."""

    return current_user

================================================
FILE: hotel-agent-backend/app/modules/identity/schemas.py
================================================
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CurrentUser(BaseModel):
    """Authenticated Supabase user available inside backend requests."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    email: str | None = None

    # This is the Supabase/Postgres auth role, normally "authenticated".
    # It is not the hotel role such as property_manager.
    auth_role: str

================================================
FILE: hotel-agent-backend/app/modules/identity/service.py
================================================
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from app.modules.identity.schemas import CurrentUser


class InvalidIdentityClaimsError(ValueError):
    """Raised when trusted JWT claims cannot identify a valid user."""


def create_current_user(
    claims: Mapping[str, Any],
) -> CurrentUser:
    """Create an application user from validated Supabase JWT claims."""

    subject = claims.get("sub")

    if not isinstance(subject, str) or not subject.strip():
        raise InvalidIdentityClaimsError(
            "JWT subject claim is missing.",
        )

    try:
        user_id = UUID(subject)
    except ValueError as exc:
        raise InvalidIdentityClaimsError(
            "JWT subject is not a valid UUID.",
        ) from exc

    auth_role = claims.get("role")

    if not isinstance(auth_role, str) or not auth_role.strip():
        raise InvalidIdentityClaimsError(
            "JWT role claim is missing.",
        )

    email_claim = claims.get("email")

    email = email_claim if isinstance(email_claim, str) else None

    return CurrentUser(
        id=user_id,
        email=email,
        auth_role=auth_role,
    )

================================================
FILE: hotel-agent-backend/app/modules/tenancy/__init__.py
================================================


================================================
FILE: hotel-agent-backend/app/modules/tenancy/enums.py
================================================
from enum import StrEnum


class LifecycleStatus(StrEnum):
    """Lifecycle state for organizations, properties, and memberships."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class OrganizationRole(StrEnum):
    """Roles granted at organization scope."""

    ORGANIZATION_OWNER = "organization_owner"
    VIEWER = "viewer"


class PropertyRole(StrEnum):
    """Roles granted at property scope."""

    PROPERTY_MANAGER = "property_manager"
    RESERVATION_MANAGER = "reservation_manager"
    RESTAURANT_MANAGER = "restaurant_manager"
    EVENT_MANAGER = "event_manager"
    OPERATIONS_MANAGER = "operations_manager"
    SUPPORT_AGENT = "support_agent"
    VIEWER = "viewer"

================================================
FILE: hotel-agent-backend/app/modules/tenancy/models.py
================================================
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.tenancy.enums import (
    LifecycleStatus,
    OrganizationRole,
    PropertyRole,
)


class Organization(Base):
    """A hotel company or hotel group."""

    __tablename__ = "organizations"
    __table_args__ = (UniqueConstraint("slug", name="uq_organizations_slug"),)

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[LifecycleStatus] = mapped_column(
        Enum(
            LifecycleStatus,
            name="organization_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
        default=LifecycleStatus.ACTIVE,
        server_default=LifecycleStatus.ACTIVE.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    properties: Mapped[list[Property]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    memberships: Mapped[list[OrganizationMembership]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Property(Base):
    """One physical hotel belonging to an organization."""

    __tablename__ = "properties"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "code",
            name="uq_properties_organization_id_code",
        ),
        # Required so PostgreSQL can target both columns from the composite
        # property-membership foreign key.
        UniqueConstraint(
            "organization_id",
            "id",
            name="uq_properties_organization_id_id",
        ),
        CheckConstraint(
            "char_length(currency) = 3 AND currency = upper(currency)",
            name="ck_properties_currency_code",
        ),
        CheckConstraint(
            "char_length(timezone) > 0",
            name="ck_properties_timezone_not_blank",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    organization_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "organizations.id",
            name="fk_properties_organization_id_organizations",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[LifecycleStatus] = mapped_column(
        Enum(
            LifecycleStatus,
            name="property_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
        default=LifecycleStatus.ACTIVE,
        server_default=LifecycleStatus.ACTIVE.value,
    )
    # Supabase Auth user UUID. A direct auth.users foreign key is intentionally
    # deferred because auth.users is outside this application's SQLAlchemy metadata.
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    organization: Mapped[Organization] = relationship(back_populates="properties")
    memberships: Mapped[list[PropertyMembership]] = relationship(
        back_populates="property",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class OrganizationMembership(Base):
    """An authenticated Supabase user assigned to an organization."""

    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "user_id",
            name="uq_organization_memberships_organization_id_user_id",
        ),
        Index("ix_organization_memberships_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    organization_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "organizations.id",
            name="fk_organization_memberships_organization_id_organizations",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    role: Mapped[OrganizationRole] = mapped_column(
        Enum(
            OrganizationRole,
            name="organization_membership_role",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
    )
    status: Mapped[LifecycleStatus] = mapped_column(
        Enum(
            LifecycleStatus,
            name="organization_membership_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
        default=LifecycleStatus.ACTIVE,
        server_default=LifecycleStatus.ACTIVE.value,
    )
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    organization: Mapped[Organization] = relationship(back_populates="memberships")


class PropertyMembership(Base):
    """An authenticated Supabase user assigned to one hotel property."""

    __tablename__ = "property_memberships"
    __table_args__ = (
        # This is the critical cross-organization safety constraint. The supplied
        # organization_id and property_id must identify the same properties row.
        ForeignKeyConstraint(
            ["organization_id", "property_id"],
            ["properties.organization_id", "properties.id"],
            name="fk_property_memberships_property_organization",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "property_id",
            "user_id",
            name="uq_property_memberships_property_id_user_id",
        ),
        Index("ix_property_memberships_user_id", "user_id"),
        Index(
            "ix_property_memberships_organization_id_property_id",
            "organization_id",
            "property_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    organization_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )
    property_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    role: Mapped[PropertyRole] = mapped_column(
        Enum(
            PropertyRole,
            name="property_membership_role",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
    )
    status: Mapped[LifecycleStatus] = mapped_column(
        Enum(
            LifecycleStatus,
            name="property_membership_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
        default=LifecycleStatus.ACTIVE,
        server_default=LifecycleStatus.ACTIVE.value,
    )
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    property: Mapped[Property] = relationship(back_populates="memberships")

================================================
FILE: hotel-agent-backend/APPLY_AND_VALIDATE.md
================================================
# PR 2 Phase 2A — Apply and validate

Run these commands from `hotel-agent-backend`.

```powershell
git switch -c feature/pr2-tenancy
```

Copy the supplied `app/` and `migrations/env.py` files into the repository.

Verify model registration:

```powershell
python -c "from app.db.models import Base; print(sorted(Base.metadata.tables.keys()))"
```

Expected:

```text
['organization_memberships', 'organizations', 'properties', 'property_memberships']
```

Run static validation before contacting Supabase:

```powershell
python -m compileall app
python -m ruff format .
python -m ruff check .
python -m mypy app
```

Generate, but do not immediately apply, the migration:

```powershell
alembic revision --autogenerate -m "create tenancy tables"
```

Review the new file in `migrations/versions/`. It should create only:

- `organizations`
- `properties`
- `organization_memberships`
- `property_memberships`
- indexes and constraints belonging to those four tables

Important constraints to confirm:

- `uq_organizations_slug`
- `uq_properties_organization_id_code`
- `uq_properties_organization_id_id`
- `uq_organization_memberships_organization_id_user_id`
- `uq_property_memberships_property_id_user_id`
- `fk_property_memberships_property_organization`
- `ON DELETE CASCADE` on organization/property ownership constraints

Also verify that downgrade drops child tables first:

1. `property_memberships`
2. `organization_memberships`
3. `properties`
4. `organizations`

Then apply:

```powershell
alembic upgrade head
alembic current
```

Do not create the same tables manually in Supabase.

## Deliberate design decisions

- Membership `status` was included because the next tenancy-context phase requires inactive memberships to be rejected.
- User UUID columns are not yet foreign keys to `auth.users`. Supabase Auth is outside the application's SQLAlchemy metadata; authentication and RLS integration will be handled in the next phases.
- IANA timezone validity should be enforced in the API schema/service layer. The database currently prevents only blank values.

================================================
FILE: hotel-agent-backend/migrations/env.py
================================================
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.db.models import Base

# Alembic configuration object created from alembic.ini.
config = context.config

settings = get_settings()

# Supabase gives us postgresql://, but Alembic is using
# SQLAlchemy's asynchronous engine with asyncpg.
database_url = make_url(settings.database_url).set(
    drivername="postgresql+asyncpg",
)

# Alembic uses ConfigParser internally.
# Escaping % prevents problems with URL-encoded passwords such as %40.
config.set_main_option(
    "sqlalchemy.url",
    database_url.render_as_string(hide_password=False).replace("%", "%%"),
)

# Configure Alembic logging from alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alembic compares this metadata with the current database
# when --autogenerate is used.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate migration SQL without opening a database connection."""

    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations using an existing database connection."""

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and execute migrations."""

    connectable = async_engine_from_config(
        config.get_section(
            config.config_ini_section,
            {},
        ),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={
            # Required for your current corporate certificate environment.
            "ssl": settings.database_ssl_mode,
            "timeout": settings.database_timeout_seconds,
        },
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations while connected to Supabase."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

================================================
FILE: hotel-agent-backend/migrations/versions/cdff641a8945_initialize_backend_foundation.py
================================================
"""initialize backend foundation

Revision ID: cdff641a8945
Revises:
Create Date: 2026-07-23 13:01:36.414808

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "cdff641a8945"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

================================================
FILE: hotel-agent-backend/migrations/versions/f97cc2fbe621_create_tenancy_tables.py
================================================
"""create tenancy tables

Revision ID: f97cc2fbe621
Revises: cdff641a8945
Create Date: 2026-07-23 16:12:05.072780

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f97cc2fbe621"
down_revision: str | Sequence[str] | None = "cdff641a8945"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "inactive",
                name="organization_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="active",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )
    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "organization_owner",
                "viewer",
                name="organization_membership_role",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "inactive",
                name="organization_membership_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="active",
            nullable=False,
        ),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_organization_memberships_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "user_id", name="uq_organization_memberships_organization_id_user_id"
        ),
    )
    op.create_index(
        "ix_organization_memberships_user_id", "organization_memberships", ["user_id"], unique=False
    )
    op.create_table(
        "properties",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "inactive",
                name="property_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="active",
            nullable=False,
        ),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(currency) = 3 AND currency = upper(currency)",
            name="ck_properties_currency_code",
        ),
        sa.CheckConstraint("char_length(timezone) > 0", name="ck_properties_timezone_not_blank"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_properties_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code", name="uq_properties_organization_id_code"),
        sa.UniqueConstraint("organization_id", "id", name="uq_properties_organization_id_id"),
    )
    op.create_table(
        "property_memberships",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("property_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "property_manager",
                "reservation_manager",
                "restaurant_manager",
                "event_manager",
                "operations_manager",
                "support_agent",
                "viewer",
                name="property_membership_role",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "inactive",
                name="property_membership_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="active",
            nullable=False,
        ),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "property_id"],
            ["properties.organization_id", "properties.id"],
            name="fk_property_memberships_property_organization",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "property_id", "user_id", name="uq_property_memberships_property_id_user_id"
        ),
    )
    op.create_index(
        "ix_property_memberships_organization_id_property_id",
        "property_memberships",
        ["organization_id", "property_id"],
        unique=False,
    )
    op.create_index(
        "ix_property_memberships_user_id", "property_memberships", ["user_id"], unique=False
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("ix_property_memberships_user_id", table_name="property_memberships")
    op.drop_index(
        "ix_property_memberships_organization_id_property_id", table_name="property_memberships"
    )
    op.drop_table("property_memberships")
    op.drop_table("properties")
    op.drop_index("ix_organization_memberships_user_id", table_name="organization_memberships")
    op.drop_table("organization_memberships")
    op.drop_table("organizations")
    # ### end Alembic commands ###

================================================
FILE: hotel-agent-backend/pyproject.toml
================================================
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "hotel-agent-backend"
version = "0.1.0"
description = "Production backend for the agentic hotel-management platform"
requires-python = ">=3.12,<3.15"
dependencies = [
    "fastapi",
    "uvicorn[standard]",
    "pydantic",
    "pydantic-settings",
    "sqlalchemy",
    "asyncpg",
    "alembic",
    "structlog",
    "pyjwt[crypto]>=2.10,<3",
]

[project.optional-dependencies]
dev = [
    "httpx",
    "mypy",
    "pytest",
    "pytest-asyncio",
    "pytest-cov",
    "ruff",
]

[tool.setuptools.packages.find]
include = ["app*"]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = [
    "E",
    "F",
    "I",
    "B",
    "UP",
    "ASYNC",
    "SIM",
    "RUF",
]
ignore = []

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
python_version = "3.12"
strict = true
warn_unreachable = true
plugins = ["pydantic.mypy"]
exclude = ["migrations/versions/"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
asyncio_default_test_loop_scope = "session"
markers = [
    "integration: tests that require a real Supabase database connection",
]
addopts = [
    "--strict-markers",
    "--strict-config",
]

================================================
FILE: hotel-agent-backend/README.md
================================================


================================================
FILE: hotel-agent-backend/tests/__init__.py
================================================


================================================
FILE: hotel-agent-backend/tests/conftest.py
================================================
import os
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Unit tests should still load even when no local .env exists,
# such as inside GitHub Actions.
if "DATABASE_URL" not in os.environ and not Path(".env").exists():
    os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/postgres"


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Provide a FastAPI test client to unit tests."""

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

================================================
FILE: hotel-agent-backend/tests/integration/conftest.py
================================================
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import engine


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Provide an isolated database transaction for each integration test."""

    async with engine.connect() as connection:
        transaction = await connection.begin()

        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            autoflush=False,
        )

        try:
            yield session
        finally:
            await session.close()

            if transaction.is_active:
                await transaction.rollback()

================================================
FILE: hotel-agent-backend/tests/integration/test_database_health.py
================================================
import os

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1",
    reason="Set RUN_INTEGRATION_TESTS=1 to run Supabase integration tests.",
)
async def test_real_supabase_database_connection() -> None:
    from app.core.database import check_database_connection

    connected = await check_database_connection()

    assert connected is True

================================================
FILE: hotel-agent-backend/tests/integration/test_tenancy_models.py
================================================
import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tenancy.enums import (
    OrganizationRole,
    PropertyRole,
)
from app.modules.tenancy.models import (
    Organization,
    OrganizationMembership,
    Property,
    PropertyMembership,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="Set RUN_INTEGRATION_TESTS=1 to run Supabase integration tests.",
    ),
]


def unique_value(prefix: str) -> str:
    """Create a unique value to avoid collisions with previous test runs."""

    return f"{prefix}-{uuid4().hex[:12]}"


async def create_organization(
    session: AsyncSession,
    *,
    name: str | None = None,
    slug: str | None = None,
) -> Organization:
    organization = Organization(
        name=name or "Integration Test Organization",
        slug=slug or unique_value("test-organization"),
    )

    session.add(organization)
    await session.flush()

    return organization


async def create_property(
    session: AsyncSession,
    *,
    organization_id: UUID,
    code: str | None = None,
    created_by: UUID | None = None,
) -> Property:
    property_ = Property(
        organization_id=organization_id,
        name="Integration Test Property",
        code=code or unique_value("property"),
        timezone="Asia/Kolkata",
        currency="INR",
        created_by=created_by or uuid4(),
    )

    session.add(property_)
    await session.flush()

    return property_


async def create_organization_membership(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID | None = None,
    role: OrganizationRole = OrganizationRole.ORGANIZATION_OWNER,
    created_by: UUID | None = None,
) -> OrganizationMembership:
    membership = OrganizationMembership(
        organization_id=organization_id,
        user_id=user_id or uuid4(),
        role=role,
        created_by=created_by or uuid4(),
    )

    session.add(membership)
    await session.flush()

    return membership


async def create_property_membership(
    session: AsyncSession,
    *,
    organization_id: UUID,
    property_id: UUID,
    user_id: UUID | None = None,
    role: PropertyRole = PropertyRole.PROPERTY_MANAGER,
    created_by: UUID | None = None,
) -> PropertyMembership:
    membership = PropertyMembership(
        organization_id=organization_id,
        property_id=property_id,
        user_id=user_id or uuid4(),
        role=role,
        created_by=created_by or uuid4(),
    )

    session.add(membership)
    await session.flush()

    return membership


async def test_organization_can_be_created(
    db_session: AsyncSession,
) -> None:
    organization = await create_organization(db_session)

    assert organization.id is not None
    assert organization.name == "Integration Test Organization"
    assert organization.slug.startswith("test-organization-")


async def test_property_can_belong_to_organization(
    db_session: AsyncSession,
) -> None:
    organization = await create_organization(db_session)

    property_ = await create_property(
        db_session,
        organization_id=organization.id,
    )

    assert property_.id is not None
    assert property_.organization_id == organization.id
    assert property_.timezone == "Asia/Kolkata"
    assert property_.currency == "INR"


async def test_duplicate_organization_slug_is_rejected(
    db_session: AsyncSession,
) -> None:
    duplicate_slug = unique_value("duplicate-slug")

    await create_organization(
        db_session,
        name="Organization One",
        slug=duplicate_slug,
    )

    duplicate_organization = Organization(
        name="Organization Two",
        slug=duplicate_slug,
    )

    db_session.add(duplicate_organization)

    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()


async def test_duplicate_property_code_in_same_organization_is_rejected(
    db_session: AsyncSession,
) -> None:
    organization = await create_organization(db_session)
    duplicate_code = unique_value("hotel")

    await create_property(
        db_session,
        organization_id=organization.id,
        code=duplicate_code,
    )

    duplicate_property = Property(
        organization_id=organization.id,
        name="Duplicate Property",
        code=duplicate_code,
        timezone="Asia/Kolkata",
        currency="INR",
        created_by=uuid4(),
    )

    db_session.add(duplicate_property)

    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()


async def test_same_property_code_in_different_organizations_is_allowed(
    db_session: AsyncSession,
) -> None:
    organization_a = await create_organization(
        db_session,
        name="Organization A",
    )
    organization_b = await create_organization(
        db_session,
        name="Organization B",
    )

    shared_code = unique_value("shared-hotel")

    property_a = await create_property(
        db_session,
        organization_id=organization_a.id,
        code=shared_code,
    )
    property_b = await create_property(
        db_session,
        organization_id=organization_b.id,
        code=shared_code,
    )

    assert property_a.code == property_b.code
    assert property_a.organization_id != property_b.organization_id


async def test_duplicate_organization_membership_is_rejected(
    db_session: AsyncSession,
) -> None:
    organization = await create_organization(db_session)
    user_id = uuid4()

    await create_organization_membership(
        db_session,
        organization_id=organization.id,
        user_id=user_id,
    )

    duplicate_membership = OrganizationMembership(
        organization_id=organization.id,
        user_id=user_id,
        role=OrganizationRole.VIEWER,
        created_by=uuid4(),
    )

    db_session.add(duplicate_membership)

    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()


async def test_duplicate_property_membership_is_rejected(
    db_session: AsyncSession,
) -> None:
    organization = await create_organization(db_session)

    property_ = await create_property(
        db_session,
        organization_id=organization.id,
    )

    user_id = uuid4()

    await create_property_membership(
        db_session,
        organization_id=organization.id,
        property_id=property_.id,
        user_id=user_id,
    )

    duplicate_membership = PropertyMembership(
        organization_id=organization.id,
        property_id=property_.id,
        user_id=user_id,
        role=PropertyRole.VIEWER,
        created_by=uuid4(),
    )

    db_session.add(duplicate_membership)

    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()


async def test_property_membership_cannot_mix_organizations(
    db_session: AsyncSession,
) -> None:
    organization_a = await create_organization(
        db_session,
        name="Organization A",
    )
    organization_b = await create_organization(
        db_session,
        name="Organization B",
    )

    property_b = await create_property(
        db_session,
        organization_id=organization_b.id,
    )

    invalid_membership = PropertyMembership(
        organization_id=organization_a.id,
        property_id=property_b.id,
        user_id=uuid4(),
        role=PropertyRole.PROPERTY_MANAGER,
        created_by=uuid4(),
    )

    db_session.add(invalid_membership)

    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()


async def test_deleting_organization_cascades_dependent_records(
    db_session: AsyncSession,
) -> None:
    organization = await create_organization(db_session)

    property_ = await create_property(
        db_session,
        organization_id=organization.id,
    )

    await create_organization_membership(
        db_session,
        organization_id=organization.id,
    )

    await create_property_membership(
        db_session,
        organization_id=organization.id,
        property_id=property_.id,
    )

    await db_session.execute(
        delete(Organization).where(
            Organization.id == organization.id,
        )
    )
    await db_session.flush()

    property_count = await db_session.scalar(
        select(func.count())
        .select_from(Property)
        .where(Property.organization_id == organization.id)
    )

    organization_membership_count = await db_session.scalar(
        select(func.count())
        .select_from(OrganizationMembership)
        .where(
            OrganizationMembership.organization_id == organization.id,
        )
    )

    property_membership_count = await db_session.scalar(
        select(func.count())
        .select_from(PropertyMembership)
        .where(
            PropertyMembership.organization_id == organization.id,
        )
    )

    assert property_count == 0
    assert organization_membership_count == 0
    assert property_membership_count == 0

================================================
FILE: hotel-agent-backend/tests/unit/test_auth_dependencies.py
================================================
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import TokenValidationError

AUTH_ME_URL = "/api/v1/auth/me"


def test_auth_me_requires_token(
    client: TestClient,
) -> None:
    response = client.get(AUTH_ME_URL)

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication required.",
    }

    assert response.headers["www-authenticate"] == "Bearer"


def test_auth_me_returns_authenticated_user(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()

    async def valid_token_decoder(
        token: str,
    ) -> dict[str, object]:
        assert token == "valid-test-token"

        return {
            "sub": str(user_id),
            "email": "manager@example.com",
            "role": "authenticated",
        }

    monkeypatch.setattr(
        "app.api.dependencies.decode_access_token",
        valid_token_decoder,
    )

    response = client.get(
        AUTH_ME_URL,
        headers={
            "Authorization": "Bearer valid-test-token",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(user_id),
        "email": "manager@example.com",
        "auth_role": "authenticated",
    }


def test_auth_me_rejects_invalid_token(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def invalid_token_decoder(
        _: str,
    ) -> dict[str, object]:
        raise TokenValidationError(
            "Token validation failed.",
        )

    monkeypatch.setattr(
        "app.api.dependencies.decode_access_token",
        invalid_token_decoder,
    )

    response = client.get(
        AUTH_ME_URL,
        headers={
            "Authorization": "Bearer invalid-test-token",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid authentication token.",
    }


def test_auth_me_rejects_malformed_user_claims(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def malformed_claims_decoder(
        _: str,
    ) -> dict[str, object]:
        return {
            "sub": "not-a-uuid",
            "role": "authenticated",
        }

    monkeypatch.setattr(
        "app.api.dependencies.decode_access_token",
        malformed_claims_decoder,
    )

    response = client.get(
        AUTH_ME_URL,
        headers={
            "Authorization": "Bearer malformed-user-token",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid authentication token.",
    }

================================================
FILE: hotel-agent-backend/tests/unit/test_health.py
================================================
import pytest
from fastapi.testclient import TestClient

LIVENESS_URL = "/health/live"
READINESS_URL = "/health/ready"


def test_root_endpoint(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "Agentic Hotel Management API",
        "documentation": "/docs",
    }


def test_liveness_returns_200(client: TestClient) -> None:
    response = client.get(LIVENESS_URL)

    assert response.status_code == 200
    assert response.json() == {
        "status": "alive",
        "service": "hotel-agent-backend",
    }


def test_readiness_returns_200_when_database_is_available(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def successful_database_check() -> bool:
        return True

    monkeypatch.setattr(
        "app.api.health.check_database_connection",
        successful_database_check,
    )

    response = client.get(READINESS_URL)

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "supabase-postgres",
    }


def test_readiness_returns_503_when_database_raises_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def failed_database_check() -> bool:
        raise RuntimeError("Test database failure")

    monkeypatch.setattr(
        "app.api.health.check_database_connection",
        failed_database_check,
    )

    response = client.get(READINESS_URL)

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Service is not ready.",
    }


def test_readiness_returns_503_on_timeout(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def timed_out_database_check() -> bool:
        raise TimeoutError("Test database timeout")

    monkeypatch.setattr(
        "app.api.health.check_database_connection",
        timed_out_database_check,
    )

    response = client.get(READINESS_URL)

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Service dependency timed out.",
    }


def test_readiness_returns_503_when_database_returns_false(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def unavailable_database_check() -> bool:
        return False

    monkeypatch.setattr(
        "app.api.health.check_database_connection",
        unavailable_database_check,
    )

    response = client.get(READINESS_URL)

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Service is not ready.",
    }


def test_request_id_is_added_to_response(
    client: TestClient,
) -> None:
    response = client.get(LIVENESS_URL)

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert "X-Response-Time-Ms" in response.headers


def test_existing_request_id_is_preserved(
    client: TestClient,
) -> None:
    request_id = "test-request-123"

    response = client.get(
        LIVENESS_URL,
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id

================================================
FILE: README.md
================================================
# Agentic-HMS

================================================
FILE: requirements.txt
================================================
# Web API
fastapi
uvicorn[standard]

# Configuration and validation
pydantic
pydantic-settings

# Database and migrations
SQLAlchemy
asyncpg
alembic

# Logging
structlog


# HTTP client
httpx

# Testing
pytest
pytest-asyncio
pytest-cov

# Code quality
ruff
mypy
