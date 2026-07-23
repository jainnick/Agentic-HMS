Directory structure:
└── Agentic-HMS/
    ├── create_repo_structure.py
    ├── README.md
    ├── requirements.txt
    └── hotel-agent-backend
        ├── .gitignore
        ├── alembic.ini
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
        │   │   └── health.py
        │   ├── core
        │   │   ├── __init__.py
        │   │   ├── config.py
        │   │   ├── database.py
        │   │   ├── exceptions.py
        │   │   ├── logging.py
        │   │   └── middleware.py
        │   └── db
        │       ├── __init__.py
        │       └── base.py
        ├── migrations
        │   ├── env.py
        │   └── versions
        │       └── cdff641a8945_initialize_backend_foundation.py
        └── tests
            ├── __init__.py
            ├── conftest.py
            ├── integration
            │   └── test_database_health.py
            └── unit
                └── test_health.py

Generated at: 2026-07-23 14:02:13
Total files included: 26

================================================
FILE: create_repo_structure.py
================================================
#!/usr/bin/env python3
"""
Create the backend repository structure for the Agentic Hotel Management System.

Default:
    python create_repo_structure.py
    Creates a `hotel-agent-backend` folder inside the current directory.

Alternative:
    python create_repo_structure.py --current
    Creates the structure directly inside the current directory.

Existing files and directories are never overwritten.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_NAME = "hotel-agent-backend"

DIRECTORIES = [
    "app",
    "app/api",
    "app/core",
    "app/db",
    "migrations",
    "migrations/versions",
    "tests",
    "tests/unit",
    "tests/integration",
    ".github",
    ".github/workflows",
]

FILES = [
    "app/__init__.py",
    "app/main.py",
    "app/api/__init__.py",
    "app/api/health.py",
    "app/core/__init__.py",
    "app/core/config.py",
    "app/core/database.py",
    "app/core/exceptions.py",
    "app/core/logging.py",
    "app/core/middleware.py",
    "app/db/__init__.py",
    "app/db/base.py",
    "migrations/env.py",
    "migrations/script.py.mako",
    "tests/__init__.py",
    "tests/conftest.py",
    "tests/unit/test_health.py",
    "tests/integration/test_database_health.py",
    ".github/workflows/backend-ci.yml",
    ".dockerignore",
    ".env.example",
    ".gitignore",
    "alembic.ini",
    "docker-compose.yml",
    "Dockerfile",
    "Makefile",
    "pyproject.toml",
    "README.md",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create the hotel-agent-backend repository structure."
    )
    parser.add_argument(
        "--current",
        action="store_true",
        help="Create the structure directly in the current directory.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help=(
            "Optional parent or target directory. Without --current, the project "
            "folder is created inside this path."
        ),
    )
    return parser.parse_args()


def resolve_target(args: argparse.Namespace) -> Path:
    base_path = (args.root or Path.cwd()).expanduser().resolve()

    if args.current:
        return base_path

    if base_path.name == PROJECT_NAME:
        return base_path

    return base_path / PROJECT_NAME


def create_directory(path: Path) -> str:
    if path.exists():
        return "skipped" if path.is_dir() else "conflict"

    path.mkdir(parents=True, exist_ok=True)
    return "created"


def create_file(path: Path) -> str:
    if path.exists():
        return "skipped" if path.is_file() else "conflict"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    return "created"


def main() -> int:
    args = parse_args()
    target = resolve_target(args)

    counters = {
        "created_directories": 0,
        "skipped_directories": 0,
        "created_files": 0,
        "skipped_files": 0,
        "conflicts": 0,
    }

    print(f"\nTarget repository: {target}\n")

    for relative_path in DIRECTORIES:
        path = target / relative_path
        result = create_directory(path)

        if result == "created":
            counters["created_directories"] += 1
            print(f"[CREATED DIR]  {path}")
        elif result == "skipped":
            counters["skipped_directories"] += 1
            print(f"[SKIPPED DIR]  {path}")
        else:
            counters["conflicts"] += 1
            print(f"[CONFLICT]     Expected directory but found file: {path}")

    for relative_path in FILES:
        path = target / relative_path
        result = create_file(path)

        if result == "created":
            counters["created_files"] += 1
            print(f"[CREATED FILE] {path}")
        elif result == "skipped":
            counters["skipped_files"] += 1
            print(f"[SKIPPED FILE] {path}")
        else:
            counters["conflicts"] += 1
            print(f"[CONFLICT]     Expected file but found directory: {path}")

    print("\nSummary")
    print("-" * 50)
    print(f"Created directories : {counters['created_directories']}")
    print(f"Skipped directories : {counters['skipped_directories']}")
    print(f"Created files       : {counters['created_files']}")
    print(f"Skipped files       : {counters['skipped_files']}")
    print(f"Conflicts           : {counters['conflicts']}")
    print(f"Repository path     : {target}")

    if counters["conflicts"]:
        print(
            "\nCompleted with conflicts. Review the paths marked [CONFLICT].",
            file=sys.stderr,
        )
        return 1

    print("\nRepository structure created successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

================================================
FILE: hotel-agent-backend/.github/workflows/backend-ci.yml
================================================


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
        raise RuntimeError(
            f"Unexpected database health-check value: {value!r}"
        )

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
FILE: hotel-agent-backend/app/main.py
================================================
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.database import close_database_connections
from app.core.middleware import RequestContextMiddleware

from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await close_database_connections()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Backend API for the Agentic Hotel Management System.",
    lifespan=lifespan,
)

app.include_router(
    health_router,
)

app.add_middleware(RequestContextMiddleware)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "documentation": "/docs",
    }

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
from app.db.base import Base


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
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cdff641a8945'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

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
    "python-json-logger",
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
markers = [
    "integration: tests that require a real Supabase database connection",
]
addopts = [
    "--strict-markers",
    "--strict-config",
    "--cov=app",
    "--cov-report=term-missing",
    "--cov-fail-under=80",
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
    os.environ["DATABASE_URL"] = (
        "postgresql://postgres:postgres@localhost:5432/postgres"
    )


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Provide a FastAPI test client to unit tests."""

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

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
