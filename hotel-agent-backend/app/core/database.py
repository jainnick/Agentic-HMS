from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()

raw_database_url = make_url(settings.database_url)

# Vercel's Supabase integration appends `sslmode=require` to POSTGRES_URL.
# That option is valid for libpq/psycopg URLs, but asyncpg receives URL query
# options as keyword arguments and rejects `sslmode`. SSL is configured below
# using asyncpg's supported `ssl` connection argument instead.
database_query = {
    key: value
    for key, value in raw_database_url.query.items()
    if key.lower() != "sslmode"
}

database_url = raw_database_url.set(
    drivername="postgresql+asyncpg",
    query=database_query,
)

# Supabase's transaction pooler uses port 6543. Serverless functions should not
# keep a second client-side pool in front of it, and asyncpg's prepared statement
# cache must be disabled for transaction-pooling mode.
uses_transaction_pooler = database_url.port == 6543

if uses_transaction_pooler:
    engine = create_async_engine(
        database_url,
        echo=settings.sql_echo,
        pool_pre_ping=True,
        poolclass=NullPool,
        connect_args={
            "ssl": settings.database_ssl_mode,
            "timeout": settings.database_timeout_seconds,
            "statement_cache_size": 0,
        },
    )
else:
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
