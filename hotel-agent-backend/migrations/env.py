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
