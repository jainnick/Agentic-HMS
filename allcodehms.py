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
        │       ├── onboarding
        │       │   ├── __init__.py
        │       │   ├── routes.py
        │       │   ├── schemas.py
        │       │   └── service.py
        │       └── tenancy
        │           ├── __init__.py
        │           ├── context.py
        │           ├── enums.py
        │           ├── models.py
        │           └── service.py
        ├── migrations
        │   ├── env.py
        │   └── versions
        │       ├── a81c4f6b2d90_add_initial_tenant_rls.py
        │       ├── cdff641a8945_initialize_backend_foundation.py
        │       └── f97cc2fbe621_create_tenancy_tables.py
        └── tests
            ├── __init__.py
            ├── conftest.py
            ├── integration
            │   ├── conftest.py
            │   ├── test_database_health.py
            │   ├── test_onboarding_service.py
            │   ├── test_tenancy_models.py
            │   └── test_tenant_context.py
            └── unit
                ├── test_auth_dependencies.py
                ├── test_health.py
                ├── test_onboarding_schemas.py
                └── test_tenant_permissions.py

Generated at: 2026-07-27 16:46:09
Total files included: 52

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
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
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
from app.modules.tenancy.context import TenantContext
from app.modules.tenancy.service import (
    TenantAccessDeniedError,
    TenantResourceNotFoundError,
    resolve_tenant_context,
)

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="Supabase access token",
)


def authentication_required_error() -> HTTPException:
    """Return a standard response when authentication is missing."""

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


def invalid_token_error() -> HTTPException:
    """Return a standard response when a token cannot be trusted."""

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
    """
    Validate a Supabase access token and return the authenticated user.

    This dependency identifies the user only. Tenant access is resolved
    separately through get_tenant_context().
    """

    if credentials is None:
        raise authentication_required_error()

    if credentials.scheme.lower() != "bearer":
        raise authentication_required_error()

    try:
        claims = await decode_access_token(
            credentials.credentials,
        )

        return create_current_user(
            claims,
        )

    except AuthConfigurationError as exc:
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


DatabaseSessionDependency = Annotated[
    AsyncSession,
    Depends(get_db_session),
]


async def get_tenant_context(
    current_user: CurrentUserDependency,
    session: DatabaseSessionDependency,
    organization_id: Annotated[
        UUID,
        Header(
            alias="X-Organization-ID",
            description="Organization selected in the Agentic HMS portal.",
        ),
    ],
    property_id: Annotated[
        UUID | None,
        Header(
            alias="X-Property-ID",
            description="Optional hotel property selected in the portal.",
        ),
    ] = None,
) -> TenantContext:
    """
    Verify the organization and optional property selected by the user.

    Header values are treated as requested values only. The tenancy service
    verifies the resources and memberships before returning TenantContext.
    """

    try:
        return await resolve_tenant_context(
            session,
            current_user=current_user,
            organization_id=organization_id,
            property_id=property_id,
        )

    except TenantResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested tenant was not found.",
        ) from exc

    except TenantAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to the requested tenant.",
        ) from exc


TenantContextDependency = Annotated[
    TenantContext,
    Depends(get_tenant_context),
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
from app.modules.onboarding.routes import router as onboarding_router

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

app.add_middleware(
    RequestContextMiddleware,
)

app.include_router(
    health_router,
)

app.include_router(
    identity_router,
    prefix=settings.api_v1_prefix,
)

app.include_router(
    onboarding_router,
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
FILE: hotel-agent-backend/app/modules/onboarding/__init__.py
================================================


================================================
FILE: hotel-agent-backend/app/modules/onboarding/routes.py
================================================
from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import (
    CurrentUserDependency,
    DatabaseSessionDependency,
)
from app.modules.onboarding.schemas import (
    OnboardingStatusResponse,
    OrganizationCreateRequest,
    OrganizationCreateResponse,
    PropertyCreateRequest,
    PropertyCreateResponse,
)
from app.modules.onboarding.service import (
    OnboardingAccessDeniedError,
    OnboardingConflictError,
    create_first_organization,
    create_first_property,
    get_onboarding_status,
)

router = APIRouter(
    prefix="/onboarding",
    tags=["Onboarding"],
)


@router.get(
    "/status",
    response_model=OnboardingStatusResponse,
)
async def read_onboarding_status(
    current_user: CurrentUserDependency,
    session: DatabaseSessionDependency,
) -> OnboardingStatusResponse:
    """Return the next onboarding step for the authenticated user."""

    return await get_onboarding_status(
        session,
        current_user=current_user,
    )


@router.post(
    "/organization",
    response_model=OrganizationCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_onboarding_organization(
    payload: OrganizationCreateRequest,
    current_user: CurrentUserDependency,
    session: DatabaseSessionDependency,
) -> OrganizationCreateResponse:
    """Create the user's first organization and owner membership."""

    try:
        organization = await create_first_organization(
            session,
            current_user=current_user,
            payload=payload,
        )

    except OnboardingConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return OrganizationCreateResponse.model_validate(
        organization,
    )


@router.post(
    "/property",
    response_model=PropertyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_onboarding_property(
    payload: PropertyCreateRequest,
    current_user: CurrentUserDependency,
    session: DatabaseSessionDependency,
) -> PropertyCreateResponse:
    """Create the first property under the user's owned organization."""

    try:
        property_ = await create_first_property(
            session,
            current_user=current_user,
            payload=payload,
        )

    except OnboardingAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except OnboardingConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return PropertyCreateResponse.model_validate(
        property_,
    )

================================================
FILE: hotel-agent-backend/app/modules/onboarding/schemas.py
================================================
from __future__ import annotations

from enum import StrEnum
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class OnboardingStep(StrEnum):
    CREATE_ORGANIZATION = "create_organization"
    CREATE_PROPERTY = "create_property"
    COMPLETED = "completed"


class OnboardingStatusResponse(BaseModel):
    """Current onboarding state for the authenticated platform user."""

    has_organization: bool
    has_property: bool
    next_step: OnboardingStep

    organization_id: UUID | None = None
    property_id: UUID | None = None


class OrganizationCreateRequest(BaseModel):
    """Details required to create the user's first hotel organization."""

    name: str = Field(
        min_length=2,
        max_length=255,
    )

    @field_validator(
        "name",
        mode="before",
    )
    @classmethod
    def normalize_name(
        cls,
        value: object,
    ) -> str:
        """
        Trim external whitespace and collapse repeated internal whitespace.

        This validator runs before Pydantic's length checks so values such as
        '  Demo   Hotels  ' are validated after normalization.
        """

        if not isinstance(value, str):
            raise ValueError(
                "Organization name must be a string.",
            )

        normalized = " ".join(
            value.strip().split(),
        )

        if not normalized:
            raise ValueError(
                "Organization name cannot be blank.",
            )

        return normalized


class OrganizationCreateResponse(BaseModel):
    """Organization created during initial onboarding."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    name: str
    slug: str


class PropertyCreateRequest(BaseModel):
    """Details required to create the user's first hotel property."""

    name: str = Field(
        min_length=2,
        max_length=255,
    )
    code: str = Field(
        min_length=2,
        max_length=64,
    )
    timezone: str = Field(
        min_length=1,
        max_length=64,
    )
    currency: str = Field(
        min_length=3,
        max_length=3,
    )

    @field_validator(
        "name",
        mode="before",
    )
    @classmethod
    def normalize_property_name(
        cls,
        value: object,
    ) -> str:
        """Normalize the property name before validating its length."""

        if not isinstance(value, str):
            raise ValueError(
                "Property name must be a string.",
            )

        normalized = " ".join(
            value.strip().split(),
        )

        if not normalized:
            raise ValueError(
                "Property name cannot be blank.",
            )

        return normalized

    @field_validator(
        "code",
        mode="before",
    )
    @classmethod
    def normalize_property_code(
        cls,
        value: object,
    ) -> str:
        """Trim and uppercase the property code before length validation."""

        if not isinstance(value, str):
            raise ValueError(
                "Property code must be a string.",
            )

        normalized = value.strip().upper()

        if not normalized:
            raise ValueError(
                "Property code cannot be blank.",
            )

        return normalized

    @field_validator(
        "currency",
        mode="before",
    )
    @classmethod
    def normalize_currency(
        cls,
        value: object,
    ) -> str:
        """
        Trim and uppercase the ISO-style currency code before validation.

        The database currently requires three uppercase characters. A complete
        ISO 4217 catalogue validation can be added later if actually needed.
        """

        if not isinstance(value, str):
            raise ValueError(
                "Currency must be a string.",
            )

        normalized = value.strip().upper()

        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError(
                "Currency must contain exactly three letters.",
            )

        return normalized

    @field_validator(
        "timezone",
        mode="before",
    )
    @classmethod
    def validate_timezone(
        cls,
        value: object,
    ) -> str:
        """Normalize and validate an IANA timezone name."""

        if not isinstance(value, str):
            raise ValueError(
                "Timezone must be a string.",
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "Timezone cannot be blank.",
            )

        try:
            ZoneInfo(normalized)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(
                "Timezone must be a valid IANA timezone.",
            ) from exc

        return normalized


class PropertyCreateResponse(BaseModel):
    """Property created during initial onboarding."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    organization_id: UUID
    name: str
    code: str
    timezone: str
    currency: str

================================================
FILE: hotel-agent-backend/app/modules/onboarding/service.py
================================================
import re

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.schemas import CurrentUser
from app.modules.onboarding.schemas import (
    OnboardingStatusResponse,
    OnboardingStep,
    OrganizationCreateRequest,
    PropertyCreateRequest,
)
from app.modules.tenancy.enums import (
    LifecycleStatus,
    OrganizationRole,
)
from app.modules.tenancy.models import (
    Organization,
    OrganizationMembership,
    Property,
)


class OnboardingError(Exception):
    """Base error for onboarding failures."""


class OnboardingConflictError(OnboardingError):
    """Raised when onboarding would duplicate an existing resource."""


class OnboardingAccessDeniedError(OnboardingError):
    """Raised when the user cannot perform the requested onboarding step."""


def slugify(
    value: str,
) -> str:
    """Convert an organization name into a URL-friendly slug."""

    normalized = value.strip().lower()

    normalized = re.sub(
        r"[^a-z0-9]+",
        "-",
        normalized,
    )

    return normalized.strip("-") or "organization"


async def generate_unique_organization_slug(
    session: AsyncSession,
    *,
    organization_name: str,
) -> str:
    """Generate a slug that is unique across organizations."""

    base_slug = slugify(
        organization_name,
    )
    candidate = base_slug
    suffix = 2

    while await session.scalar(
        select(Organization.id).where(
            Organization.slug == candidate,
        )
    ):
        candidate = f"{base_slug}-{suffix}"
        suffix += 1

    return candidate


async def get_onboarding_status(
    session: AsyncSession,
    *,
    current_user: CurrentUser,
) -> OnboardingStatusResponse:
    """Determine the user's onboarding state from existing tenant data."""

    organization_membership = await session.execute(
        select(
            OrganizationMembership.organization_id,
        )
        .where(
            OrganizationMembership.user_id == current_user.id,
            OrganizationMembership.status == LifecycleStatus.ACTIVE,
        )
        .order_by(
            OrganizationMembership.created_at.asc(),
        )
        .limit(1)
    )

    organization_id = organization_membership.scalar_one_or_none()

    if organization_id is None:
        return OnboardingStatusResponse(
            has_organization=False,
            has_property=False,
            next_step=OnboardingStep.CREATE_ORGANIZATION,
        )

    property_id = await session.scalar(
        select(Property.id)
        .where(
            Property.organization_id == organization_id,
            Property.status == LifecycleStatus.ACTIVE,
        )
        .order_by(
            Property.created_at.asc(),
        )
        .limit(1)
    )

    if property_id is None:
        return OnboardingStatusResponse(
            has_organization=True,
            has_property=False,
            next_step=OnboardingStep.CREATE_PROPERTY,
            organization_id=organization_id,
        )

    return OnboardingStatusResponse(
        has_organization=True,
        has_property=True,
        next_step=OnboardingStep.COMPLETED,
        organization_id=organization_id,
        property_id=property_id,
    )


async def create_first_organization(
    session: AsyncSession,
    *,
    current_user: CurrentUser,
    payload: OrganizationCreateRequest,
) -> Organization:
    """
    Create the user's first organization and owner membership atomically.

    The authenticated user automatically becomes organization_owner.
    """

    existing_membership = await session.scalar(
        select(OrganizationMembership.id).where(
            OrganizationMembership.user_id == current_user.id,
            OrganizationMembership.status == LifecycleStatus.ACTIVE,
        )
    )

    if existing_membership is not None:
        raise OnboardingConflictError(
            "The user already belongs to an organization.",
        )

    slug = await generate_unique_organization_slug(
        session,
        organization_name=payload.name,
    )

    organization = Organization(
        name=payload.name,
        slug=slug,
    )

    try:
        session.add(
            organization,
        )
        await session.flush()

        owner_membership = OrganizationMembership(
            organization_id=organization.id,
            user_id=current_user.id,
            role=OrganizationRole.ORGANIZATION_OWNER,
            created_by=current_user.id,
        )

        session.add(
            owner_membership,
        )

        await session.commit()
        await session.refresh(
            organization,
        )

    except IntegrityError as exc:
        await session.rollback()

        raise OnboardingConflictError(
            "The organization could not be created because of a conflicting record.",
        ) from exc

    except Exception:
        await session.rollback()
        raise

    return organization


async def create_first_property(
    session: AsyncSession,
    *,
    current_user: CurrentUser,
    payload: PropertyCreateRequest,
) -> Property:
    """
    Create the first property under the user's owned organization.

    The organization ID and created_by value are derived from the authenticated
    user's active organization-owner membership.
    """

    organization_id = await session.scalar(
        select(
            OrganizationMembership.organization_id,
        ).where(
            OrganizationMembership.user_id == current_user.id,
            OrganizationMembership.role == OrganizationRole.ORGANIZATION_OWNER,
            OrganizationMembership.status == LifecycleStatus.ACTIVE,
        )
    )

    if organization_id is None:
        raise OnboardingAccessDeniedError(
            "An active organization-owner membership is required.",
        )

    existing_property_count = await session.scalar(
        select(
            func.count(Property.id),
        ).where(
            Property.organization_id == organization_id,
        )
    )

    if existing_property_count and existing_property_count > 0:
        raise OnboardingConflictError(
            "The organization already has a property.",
        )

    property_ = Property(
        organization_id=organization_id,
        name=payload.name,
        code=payload.code,
        timezone=payload.timezone,
        currency=payload.currency,
        created_by=current_user.id,
    )

    try:
        session.add(
            property_,
        )

        await session.commit()
        await session.refresh(
            property_,
        )

    except IntegrityError as exc:
        await session.rollback()

        raise OnboardingConflictError(
            "The property code is already used by this organization.",
        ) from exc

    except Exception:
        await session.rollback()
        raise

    return property_

================================================
FILE: hotel-agent-backend/app/modules/tenancy/__init__.py
================================================


================================================
FILE: hotel-agent-backend/app/modules/tenancy/context.py
================================================
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.modules.tenancy.enums import (
    OrganizationRole,
    PropertyRole,
)


class TenantContext(BaseModel):
    """
    Verified organization and property scope for an authenticated request.

    This object must be created only after the backend has checked:
    - the organization exists and is active;
    - the property exists and belongs to the organization;
    - the authenticated user has an active organization or property membership.
    """

    model_config = ConfigDict(
        frozen=True,
    )

    user_id: UUID
    organization_id: UUID
    property_id: UUID | None = None

    organization_role: OrganizationRole | None = None
    property_role: PropertyRole | None = None

    @model_validator(mode="after")
    def validate_tenant_context(self) -> TenantContext:
        """
        Prevent invalid tenant-context combinations.

        A property role cannot exist unless a property is selected, and at
        least one verified membership role must be present.
        """

        if self.property_id is None and self.property_role is not None:
            raise ValueError(
                "property_role cannot be provided without property_id.",
            )

        if self.organization_role is None and self.property_role is None:
            raise ValueError(
                "Tenant context requires at least one verified membership role.",
            )

        return self

    @property
    def is_organization_scope(self) -> bool:
        """Return True when the request operates only at organization level."""

        return self.property_id is None

    @property
    def is_property_scope(self) -> bool:
        """Return True when the request operates on a specific hotel property."""

        return self.property_id is not None

    @property
    def role_names(self) -> frozenset[str]:
        """Return all verified organization and property role names."""

        roles: set[str] = set()

        if self.organization_role is not None:
            roles.add(self.organization_role.value)

        if self.property_role is not None:
            roles.add(self.property_role.value)

        return frozenset(roles)

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
FILE: hotel-agent-backend/app/modules/tenancy/service.py
================================================
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.schemas import CurrentUser
from app.modules.tenancy.context import TenantContext
from app.modules.tenancy.enums import (
    LifecycleStatus,
    OrganizationRole,
    PropertyRole,
)
from app.modules.tenancy.models import (
    Organization,
    OrganizationMembership,
    Property,
    PropertyMembership,
)


class TenantContextResolutionError(Exception):
    """Base error for tenant-context resolution failures."""


class TenantResourceNotFoundError(TenantContextResolutionError):
    """Raised when an active organization or property cannot be found."""


class TenantAccessDeniedError(TenantContextResolutionError):
    """Raised when the user has no active membership for the requested scope."""


async def resolve_tenant_context(
    session: AsyncSession,
    *,
    current_user: CurrentUser,
    organization_id: UUID,
    property_id: UUID | None = None,
) -> TenantContext:
    """
    Resolve a verified organization/property context for an authenticated user.

    The client may request an organization and property, but this function
    verifies that:

    - the organization exists and is active;
    - the property exists, is active, and belongs to the organization;
    - the user has an active organization or property membership.

    Organization-scope requests require an organization membership.
    Property-scope requests allow either an organization membership or a
    property-specific membership.
    """

    organization_statement = (
        select(
            Organization.id,
            OrganizationMembership.role,
        )
        .outerjoin(
            OrganizationMembership,
            and_(
                OrganizationMembership.organization_id == Organization.id,
                OrganizationMembership.user_id == current_user.id,
                OrganizationMembership.status == LifecycleStatus.ACTIVE,
            ),
        )
        .where(
            Organization.id == organization_id,
            Organization.status == LifecycleStatus.ACTIVE,
        )
    )

    organization_row = (
        await session.execute(
            organization_statement,
        )
    ).one_or_none()

    if organization_row is None:
        raise TenantResourceNotFoundError(
            "The requested organization was not found or is inactive.",
        )

    organization_role = organization_row[1]

    if property_id is None:
        if organization_role is None:
            raise TenantAccessDeniedError(
                "The user does not have access to this organization.",
            )

        return TenantContext(
            user_id=current_user.id,
            organization_id=organization_id,
            property_id=None,
            organization_role=organization_role,
            property_role=None,
        )

    property_statement = (
        select(
            Property.id,
            PropertyMembership.role,
        )
        .outerjoin(
            PropertyMembership,
            and_(
                PropertyMembership.organization_id == Property.organization_id,
                PropertyMembership.property_id == Property.id,
                PropertyMembership.user_id == current_user.id,
                PropertyMembership.status == LifecycleStatus.ACTIVE,
            ),
        )
        .where(
            Property.id == property_id,
            Property.organization_id == organization_id,
            Property.status == LifecycleStatus.ACTIVE,
        )
    )

    property_row = (
        await session.execute(
            property_statement,
        )
    ).one_or_none()

    if property_row is None:
        raise TenantResourceNotFoundError(
            "The requested property was not found, is inactive, "
            "or does not belong to the organization.",
        )

    property_role = property_row[1]

    if organization_role is None and property_role is None:
        raise TenantAccessDeniedError(
            "The user does not have access to this property.",
        )

    return TenantContext(
        user_id=current_user.id,
        organization_id=organization_id,
        property_id=property_id,
        organization_role=organization_role,
        property_role=property_role,
    )


def require_organization_owner(
    tenant_context: TenantContext,
) -> None:
    """
    Require organization-owner access.

    This is used for organization-wide operations such as creating properties,
    managing organization settings, and inviting organization administrators.
    """

    if tenant_context.organization_role != OrganizationRole.ORGANIZATION_OWNER:
        raise TenantAccessDeniedError(
            "Organization owner access is required.",
        )


def require_property_management_access(
    tenant_context: TenantContext,
) -> None:
    """
    Require permission to manage the selected hotel property.

    Organization owners may manage every property in their organization.
    Property and operations managers may manage their assigned property.
    """

    if tenant_context.organization_role == OrganizationRole.ORGANIZATION_OWNER:
        return

    allowed_property_roles = {
        PropertyRole.PROPERTY_MANAGER,
        PropertyRole.OPERATIONS_MANAGER,
    }

    if tenant_context.property_role not in allowed_property_roles:
        raise TenantAccessDeniedError(
            "Property management access is required.",
        )

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
FILE: hotel-agent-backend/migrations/versions/a81c4f6b2d90_add_initial_tenant_rls.py
================================================
"""add initial tenant rls

Revision ID: a81c4f6b2d90
Revises: f97cc2fbe621
Create Date: 2026-07-27

"""

from collections.abc import Sequence

from alembic import op

revision: str = "a81c4f6b2d90"
down_revision: str | Sequence[str] | None = "f97cc2fbe621"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Enable tenant-aware read isolation for Supabase authenticated users.

    Direct writes through Supabase REST are intentionally not allowed yet.
    All onboarding and administrative writes continue through the FastAPI
    backend.
    """

    op.execute(
        """
        CREATE SCHEMA IF NOT EXISTS private
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION private.can_access_organization(
            target_organization_id uuid
        )
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
            SELECT
                EXISTS (
                    SELECT 1
                    FROM public.organization_memberships AS membership
                    WHERE membership.organization_id = target_organization_id
                      AND membership.user_id = (SELECT auth.uid())
                      AND membership.status = 'active'
                )
                OR EXISTS (
                    SELECT 1
                    FROM public.property_memberships AS membership
                    WHERE membership.organization_id = target_organization_id
                      AND membership.user_id = (SELECT auth.uid())
                      AND membership.status = 'active'
                );
        $$
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION private.can_access_property(
            target_organization_id uuid,
            target_property_id uuid
        )
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
            SELECT
                EXISTS (
                    SELECT 1
                    FROM public.organization_memberships AS membership
                    WHERE membership.organization_id = target_organization_id
                      AND membership.user_id = (SELECT auth.uid())
                      AND membership.status = 'active'
                )
                OR EXISTS (
                    SELECT 1
                    FROM public.property_memberships AS membership
                    WHERE membership.organization_id = target_organization_id
                      AND membership.property_id = target_property_id
                      AND membership.user_id = (SELECT auth.uid())
                      AND membership.status = 'active'
                );
        $$
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION private.is_organization_owner(
            target_organization_id uuid
        )
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
            SELECT EXISTS (
                SELECT 1
                FROM public.organization_memberships AS membership
                WHERE membership.organization_id = target_organization_id
                  AND membership.user_id = (SELECT auth.uid())
                  AND membership.role = 'organization_owner'
                  AND membership.status = 'active'
            );
        $$
        """
    )

    op.execute(
        """
        REVOKE ALL
        ON FUNCTION private.can_access_organization(uuid)
        FROM PUBLIC
        """
    )

    op.execute(
        """
        REVOKE ALL
        ON FUNCTION private.can_access_property(uuid, uuid)
        FROM PUBLIC
        """
    )

    op.execute(
        """
        REVOKE ALL
        ON FUNCTION private.is_organization_owner(uuid)
        FROM PUBLIC
        """
    )

    op.execute(
        """
        GRANT USAGE ON SCHEMA private TO authenticated
        """
    )

    op.execute(
        """
        GRANT EXECUTE
        ON FUNCTION private.can_access_organization(uuid)
        TO authenticated
        """
    )

    op.execute(
        """
        GRANT EXECUTE
        ON FUNCTION private.can_access_property(uuid, uuid)
        TO authenticated
        """
    )

    op.execute(
        """
        GRANT EXECUTE
        ON FUNCTION private.is_organization_owner(uuid)
        TO authenticated
        """
    )

    op.execute(
        """
        GRANT SELECT ON
            public.organizations,
            public.properties,
            public.organization_memberships,
            public.property_memberships
        TO authenticated
        """
    )

    op.execute("ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.properties ENABLE ROW LEVEL SECURITY")
    op.execute(
        "ALTER TABLE public.organization_memberships ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE public.property_memberships ENABLE ROW LEVEL SECURITY"
    )

    op.execute(
        """
        CREATE POLICY organizations_select_for_members
        ON public.organizations
        FOR SELECT
        TO authenticated
        USING (
            private.can_access_organization(id)
        )
        """
    )

    op.execute(
        """
        CREATE POLICY properties_select_for_members
        ON public.properties
        FOR SELECT
        TO authenticated
        USING (
            private.can_access_property(
                organization_id,
                id
            )
        )
        """
    )

    op.execute(
        """
        CREATE POLICY organization_memberships_select
        ON public.organization_memberships
        FOR SELECT
        TO authenticated
        USING (
            user_id = (SELECT auth.uid())
            OR private.is_organization_owner(organization_id)
        )
        """
    )

    op.execute(
        """
        CREATE POLICY property_memberships_select
        ON public.property_memberships
        FOR SELECT
        TO authenticated
        USING (
            user_id = (SELECT auth.uid())
            OR private.is_organization_owner(organization_id)
        )
        """
    )


def downgrade() -> None:
    """Remove the initial tenant RLS configuration."""

    op.execute(
        """
        DROP POLICY IF EXISTS property_memberships_select
        ON public.property_memberships
        """
    )

    op.execute(
        """
        DROP POLICY IF EXISTS organization_memberships_select
        ON public.organization_memberships
        """
    )

    op.execute(
        """
        DROP POLICY IF EXISTS properties_select_for_members
        ON public.properties
        """
    )

    op.execute(
        """
        DROP POLICY IF EXISTS organizations_select_for_members
        ON public.organizations
        """
    )

    op.execute(
        "ALTER TABLE public.property_memberships DISABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE public.organization_memberships DISABLE ROW LEVEL SECURITY"
    )
    op.execute("ALTER TABLE public.properties DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.organizations DISABLE ROW LEVEL SECURITY")

    op.execute(
        """
        REVOKE SELECT ON
            public.organizations,
            public.properties,
            public.organization_memberships,
            public.property_memberships
        FROM authenticated
        """
    )

    op.execute(
        """
        DROP FUNCTION IF EXISTS private.is_organization_owner(uuid)
        """
    )

    op.execute(
        """
        DROP FUNCTION IF EXISTS private.can_access_property(uuid, uuid)
        """
    )

    op.execute(
        """
        DROP FUNCTION IF EXISTS private.can_access_organization(uuid)
        """
    )

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
    "tzdata",
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

# Unit tests must be able to import the application even when no local
# .env file exists, such as inside GitHub Actions.
#
# This URL is only used during unit-test application startup. Unit tests
# mock database calls and do not connect to this database.
if "DATABASE_URL" not in os.environ and not Path(".env").exists():
    os.environ["DATABASE_URL"] = (
        "postgresql://postgres:postgres@localhost:5432/postgres"
    )


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Provide a FastAPI test client to all unit tests."""

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
    """
    Provide an isolated database session for each integration test.

    Application services may call session.commit(). The session therefore
    uses a savepoint so those service commits do not commit the fixture's
    outer transaction.

    At the end of every test, rolling back the outer transaction removes
    everything created by that test.
    """

    async with engine.connect() as connection:
        outer_transaction = await connection.begin()

        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            autoflush=False,
            join_transaction_mode="create_savepoint",
        )

        try:
            yield session
        finally:
            await session.close()

            if outer_transaction.is_active:
                await outer_transaction.rollback()

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
FILE: hotel-agent-backend/tests/integration/test_onboarding_service.py
================================================
import os
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.schemas import CurrentUser
from app.modules.onboarding.schemas import (
    OnboardingStep,
    OrganizationCreateRequest,
    PropertyCreateRequest,
)
from app.modules.onboarding.service import (
    OnboardingAccessDeniedError,
    OnboardingConflictError,
    create_first_organization,
    create_first_property,
    get_onboarding_status,
)
from app.modules.tenancy.enums import (
    LifecycleStatus,
    OrganizationRole,
)
from app.modules.tenancy.models import (
    Organization,
    OrganizationMembership,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="Set RUN_INTEGRATION_TESTS=1 to run Supabase integration tests.",
    ),
]


def create_test_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        email="integration-user@example.com",
        auth_role="authenticated",
    )


def create_organization_payload() -> OrganizationCreateRequest:
    return OrganizationCreateRequest(
        name=f"Integration Hotels {uuid4().hex[:8]}",
    )


def create_property_payload(
    *,
    code: str | None = None,
) -> PropertyCreateRequest:
    return PropertyCreateRequest(
        name="Integration Hotel Delhi",
        code=code or f"DEL-{uuid4().hex[:8]}",
        timezone="Asia/Kolkata",
        currency="INR",
    )


async def test_new_user_must_create_organization(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()

    onboarding_status = await get_onboarding_status(
        db_session,
        current_user=current_user,
    )

    assert onboarding_status.has_organization is False
    assert onboarding_status.has_property is False
    assert onboarding_status.next_step == OnboardingStep.CREATE_ORGANIZATION
    assert onboarding_status.organization_id is None
    assert onboarding_status.property_id is None


async def test_creating_organization_also_creates_owner_membership(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()

    organization = await create_first_organization(
        db_session,
        current_user=current_user,
        payload=create_organization_payload(),
    )

    membership = await db_session.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization.id,
            OrganizationMembership.user_id == current_user.id,
        )
    )

    assert membership is not None
    assert membership.organization_id == organization.id
    assert membership.user_id == current_user.id
    assert membership.role == OrganizationRole.ORGANIZATION_OWNER
    assert membership.status == LifecycleStatus.ACTIVE
    assert membership.created_by == current_user.id


async def test_organization_owner_must_create_property_next(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()

    organization = await create_first_organization(
        db_session,
        current_user=current_user,
        payload=create_organization_payload(),
    )

    onboarding_status = await get_onboarding_status(
        db_session,
        current_user=current_user,
    )

    assert onboarding_status.has_organization is True
    assert onboarding_status.has_property is False
    assert onboarding_status.next_step == OnboardingStep.CREATE_PROPERTY
    assert onboarding_status.organization_id == organization.id
    assert onboarding_status.property_id is None


async def test_creating_first_property_completes_onboarding(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()

    organization = await create_first_organization(
        db_session,
        current_user=current_user,
        payload=create_organization_payload(),
    )

    property_ = await create_first_property(
        db_session,
        current_user=current_user,
        payload=create_property_payload(),
    )

    onboarding_status = await get_onboarding_status(
        db_session,
        current_user=current_user,
    )

    assert property_.organization_id == organization.id
    assert property_.created_by == current_user.id

    assert onboarding_status.has_organization is True
    assert onboarding_status.has_property is True
    assert onboarding_status.next_step == OnboardingStep.COMPLETED
    assert onboarding_status.organization_id == organization.id
    assert onboarding_status.property_id == property_.id


async def test_user_cannot_create_second_initial_organization(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()

    await create_first_organization(
        db_session,
        current_user=current_user,
        payload=create_organization_payload(),
    )

    with pytest.raises(
        OnboardingConflictError,
        match="already belongs to an organization",
    ):
        await create_first_organization(
            db_session,
            current_user=current_user,
            payload=create_organization_payload(),
        )


async def test_non_owner_cannot_create_initial_property(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()

    organization = Organization(
        name="Viewer Organization",
        slug=f"viewer-{uuid4().hex}",
    )

    db_session.add(
        organization,
    )
    await db_session.flush()

    membership = OrganizationMembership(
        organization_id=organization.id,
        user_id=current_user.id,
        role=OrganizationRole.VIEWER,
        status=LifecycleStatus.ACTIVE,
        created_by=current_user.id,
    )

    db_session.add(
        membership,
    )
    await db_session.flush()

    with pytest.raises(
        OnboardingAccessDeniedError,
        match="organization-owner membership is required",
    ):
        await create_first_property(
            db_session,
            current_user=current_user,
            payload=create_property_payload(),
        )


async def test_organization_cannot_create_second_initial_property(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()

    await create_first_organization(
        db_session,
        current_user=current_user,
        payload=create_organization_payload(),
    )

    await create_first_property(
        db_session,
        current_user=current_user,
        payload=create_property_payload(),
    )

    with pytest.raises(
        OnboardingConflictError,
        match="already has a property",
    ):
        await create_first_property(
            db_session,
            current_user=current_user,
            payload=create_property_payload(),
        )

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
FILE: hotel-agent-backend/tests/integration/test_tenant_context.py
================================================
import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.schemas import CurrentUser
from app.modules.tenancy.enums import (
    LifecycleStatus,
    OrganizationRole,
    PropertyRole,
)
from app.modules.tenancy.models import (
    Organization,
    OrganizationMembership,
    Property,
    PropertyMembership,
)
from app.modules.tenancy.service import (
    TenantAccessDeniedError,
    TenantResourceNotFoundError,
    resolve_tenant_context,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="Set RUN_INTEGRATION_TESTS=1 to run Supabase integration tests.",
    ),
]


def create_test_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        email="tenant-user@example.com",
        auth_role="authenticated",
    )


async def create_organization(
    session: AsyncSession,
    *,
    status: LifecycleStatus = LifecycleStatus.ACTIVE,
) -> Organization:
    organization = Organization(
        name="Tenant Test Organization",
        slug=f"tenant-{uuid4().hex}",
        status=status,
    )

    session.add(
        organization,
    )
    await session.flush()

    return organization


async def create_property(
    session: AsyncSession,
    *,
    organization_id: UUID,
    status: LifecycleStatus = LifecycleStatus.ACTIVE,
) -> Property:
    property_ = Property(
        organization_id=organization_id,
        name="Tenant Test Property",
        code=f"PROP-{uuid4().hex[:8]}",
        timezone="Asia/Kolkata",
        currency="INR",
        status=status,
        created_by=uuid4(),
    )

    session.add(
        property_,
    )
    await session.flush()

    return property_


async def create_organization_membership(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    role: OrganizationRole = OrganizationRole.ORGANIZATION_OWNER,
    status: LifecycleStatus = LifecycleStatus.ACTIVE,
) -> OrganizationMembership:
    membership = OrganizationMembership(
        organization_id=organization_id,
        user_id=user_id,
        role=role,
        status=status,
        created_by=user_id,
    )

    session.add(
        membership,
    )
    await session.flush()

    return membership


async def create_property_membership(
    session: AsyncSession,
    *,
    organization_id: UUID,
    property_id: UUID,
    user_id: UUID,
    role: PropertyRole = PropertyRole.PROPERTY_MANAGER,
    status: LifecycleStatus = LifecycleStatus.ACTIVE,
) -> PropertyMembership:
    membership = PropertyMembership(
        organization_id=organization_id,
        property_id=property_id,
        user_id=user_id,
        role=role,
        status=status,
        created_by=user_id,
    )

    session.add(
        membership,
    )
    await session.flush()

    return membership


async def test_organization_owner_can_access_organization(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()
    organization = await create_organization(db_session)

    await create_organization_membership(
        db_session,
        organization_id=organization.id,
        user_id=current_user.id,
    )

    tenant_context = await resolve_tenant_context(
        db_session,
        current_user=current_user,
        organization_id=organization.id,
    )

    assert tenant_context.user_id == current_user.id
    assert tenant_context.organization_id == organization.id
    assert tenant_context.property_id is None
    assert tenant_context.organization_role == OrganizationRole.ORGANIZATION_OWNER
    assert tenant_context.property_role is None


async def test_organization_owner_can_access_property(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()
    organization = await create_organization(db_session)

    property_ = await create_property(
        db_session,
        organization_id=organization.id,
    )

    await create_organization_membership(
        db_session,
        organization_id=organization.id,
        user_id=current_user.id,
    )

    tenant_context = await resolve_tenant_context(
        db_session,
        current_user=current_user,
        organization_id=organization.id,
        property_id=property_.id,
    )

    assert tenant_context.organization_id == organization.id
    assert tenant_context.property_id == property_.id
    assert tenant_context.organization_role == OrganizationRole.ORGANIZATION_OWNER


async def test_property_manager_can_access_assigned_property(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()
    organization = await create_organization(db_session)

    property_ = await create_property(
        db_session,
        organization_id=organization.id,
    )

    await create_property_membership(
        db_session,
        organization_id=organization.id,
        property_id=property_.id,
        user_id=current_user.id,
    )

    tenant_context = await resolve_tenant_context(
        db_session,
        current_user=current_user,
        organization_id=organization.id,
        property_id=property_.id,
    )

    assert tenant_context.organization_role is None
    assert tenant_context.property_role == PropertyRole.PROPERTY_MANAGER
    assert tenant_context.property_id == property_.id


async def test_property_manager_cannot_access_another_property(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()
    organization = await create_organization(db_session)

    assigned_property = await create_property(
        db_session,
        organization_id=organization.id,
    )

    other_property = await create_property(
        db_session,
        organization_id=organization.id,
    )

    await create_property_membership(
        db_session,
        organization_id=organization.id,
        property_id=assigned_property.id,
        user_id=current_user.id,
    )

    with pytest.raises(
        TenantAccessDeniedError,
        match="does not have access to this property",
    ):
        await resolve_tenant_context(
            db_session,
            current_user=current_user,
            organization_id=organization.id,
            property_id=other_property.id,
        )


async def test_inactive_organization_membership_is_rejected(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()
    organization = await create_organization(db_session)

    await create_organization_membership(
        db_session,
        organization_id=organization.id,
        user_id=current_user.id,
        status=LifecycleStatus.INACTIVE,
    )

    with pytest.raises(TenantAccessDeniedError):
        await resolve_tenant_context(
            db_session,
            current_user=current_user,
            organization_id=organization.id,
        )


async def test_inactive_property_membership_is_rejected(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()
    organization = await create_organization(db_session)

    property_ = await create_property(
        db_session,
        organization_id=organization.id,
    )

    await create_property_membership(
        db_session,
        organization_id=organization.id,
        property_id=property_.id,
        user_id=current_user.id,
        status=LifecycleStatus.INACTIVE,
    )

    with pytest.raises(TenantAccessDeniedError):
        await resolve_tenant_context(
            db_session,
            current_user=current_user,
            organization_id=organization.id,
            property_id=property_.id,
        )


async def test_property_from_another_organization_is_rejected(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()

    organization_a = await create_organization(db_session)
    organization_b = await create_organization(db_session)

    property_b = await create_property(
        db_session,
        organization_id=organization_b.id,
    )

    await create_organization_membership(
        db_session,
        organization_id=organization_a.id,
        user_id=current_user.id,
    )

    with pytest.raises(TenantResourceNotFoundError):
        await resolve_tenant_context(
            db_session,
            current_user=current_user,
            organization_id=organization_a.id,
            property_id=property_b.id,
        )


async def test_unknown_organization_is_rejected(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()

    with pytest.raises(TenantResourceNotFoundError):
        await resolve_tenant_context(
            db_session,
            current_user=current_user,
            organization_id=uuid4(),
        )


async def test_known_organization_without_membership_is_rejected(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()
    organization = await create_organization(db_session)

    with pytest.raises(TenantAccessDeniedError):
        await resolve_tenant_context(
            db_session,
            current_user=current_user,
            organization_id=organization.id,
        )

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
FILE: hotel-agent-backend/tests/unit/test_onboarding_schemas.py
================================================
import pytest
from pydantic import ValidationError

from app.modules.onboarding.schemas import (
    OrganizationCreateRequest,
    PropertyCreateRequest,
)


def test_organization_name_is_normalized() -> None:
    payload = OrganizationCreateRequest(
        name="   Demo    Hotels   Private   Limited   ",
    )

    assert payload.name == "Demo Hotels Private Limited"


def test_property_fields_are_normalized() -> None:
    payload = PropertyCreateRequest(
        name="   Demo    Hotel   Delhi   ",
        code="  del-01  ",
        timezone="Asia/Kolkata",
        currency=" inr ",
    )

    assert payload.name == "Demo Hotel Delhi"
    assert payload.code == "DEL-01"
    assert payload.timezone == "Asia/Kolkata"
    assert payload.currency == "INR"


@pytest.mark.parametrize(
    "timezone",
    [
        "",
        "Invalid/Timezone",
        "India/NewDelhi",
        "Mars/Olympus",
    ],
)
def test_invalid_timezone_is_rejected(
    timezone: str,
) -> None:
    with pytest.raises(ValidationError):
        PropertyCreateRequest(
            name="Demo Hotel",
            code="DEL01",
            timezone=timezone,
            currency="INR",
        )


@pytest.mark.parametrize(
    "currency",
    [
        "IN",
        "INRR",
        "1NR",
        "₹₹₹",
        "",
    ],
)
def test_invalid_currency_is_rejected(
    currency: str,
) -> None:
    with pytest.raises(ValidationError):
        PropertyCreateRequest(
            name="Demo Hotel",
            code="DEL01",
            timezone="Asia/Kolkata",
            currency=currency,
        )


@pytest.mark.parametrize(
    "name",
    [
        "",
        " ",
        "A",
    ],
)
def test_invalid_organization_name_is_rejected(
    name: str,
) -> None:
    with pytest.raises(ValidationError):
        OrganizationCreateRequest(
            name=name,
        )


@pytest.mark.parametrize(
    "code",
    [
        "",
        " ",
        "A",
    ],
)
def test_invalid_property_code_is_rejected(
    code: str,
) -> None:
    with pytest.raises(ValidationError):
        PropertyCreateRequest(
            name="Demo Hotel",
            code=code,
            timezone="Asia/Kolkata",
            currency="INR",
        )

================================================
FILE: hotel-agent-backend/tests/unit/test_tenant_permissions.py
================================================
from uuid import uuid4

import pytest

from app.modules.tenancy.context import TenantContext
from app.modules.tenancy.enums import (
    OrganizationRole,
    PropertyRole,
)
from app.modules.tenancy.service import (
    TenantAccessDeniedError,
    require_organization_owner,
    require_property_management_access,
)


def create_tenant_context(
    *,
    organization_role: OrganizationRole | None = None,
    property_role: PropertyRole | None = None,
    property_scope: bool = False,
) -> TenantContext:
    return TenantContext(
        user_id=uuid4(),
        organization_id=uuid4(),
        property_id=uuid4() if property_scope else None,
        organization_role=organization_role,
        property_role=property_role,
    )


def test_organization_owner_permission_is_allowed() -> None:
    tenant_context = create_tenant_context(
        organization_role=OrganizationRole.ORGANIZATION_OWNER,
    )

    require_organization_owner(
        tenant_context,
    )


def test_organization_viewer_is_not_an_owner() -> None:
    tenant_context = create_tenant_context(
        organization_role=OrganizationRole.VIEWER,
    )

    with pytest.raises(
        TenantAccessDeniedError,
        match="Organization owner access is required",
    ):
        require_organization_owner(
            tenant_context,
        )


def test_property_manager_is_not_an_organization_owner() -> None:
    tenant_context = create_tenant_context(
        property_role=PropertyRole.PROPERTY_MANAGER,
        property_scope=True,
    )

    with pytest.raises(
        TenantAccessDeniedError,
        match="Organization owner access is required",
    ):
        require_organization_owner(
            tenant_context,
        )


def test_organization_owner_can_manage_property() -> None:
    tenant_context = create_tenant_context(
        organization_role=OrganizationRole.ORGANIZATION_OWNER,
        property_scope=True,
    )

    require_property_management_access(
        tenant_context,
    )


def test_property_manager_can_manage_property() -> None:
    tenant_context = create_tenant_context(
        property_role=PropertyRole.PROPERTY_MANAGER,
        property_scope=True,
    )

    require_property_management_access(
        tenant_context,
    )


def test_operations_manager_can_manage_property() -> None:
    tenant_context = create_tenant_context(
        property_role=PropertyRole.OPERATIONS_MANAGER,
        property_scope=True,
    )

    require_property_management_access(
        tenant_context,
    )


@pytest.mark.parametrize(
    "property_role",
    [
        PropertyRole.RESERVATION_MANAGER,
        PropertyRole.RESTAURANT_MANAGER,
        PropertyRole.EVENT_MANAGER,
        PropertyRole.SUPPORT_AGENT,
        PropertyRole.VIEWER,
    ],
)
def test_other_property_roles_cannot_manage_property(
    property_role: PropertyRole,
) -> None:
    tenant_context = create_tenant_context(
        property_role=property_role,
        property_scope=True,
    )

    with pytest.raises(
        TenantAccessDeniedError,
        match="Property management access is required",
    ):
        require_property_management_access(
            tenant_context,
        )

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
tzdata

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
