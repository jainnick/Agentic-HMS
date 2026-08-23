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

database_url = make_url(settings.database_url).set(
    drivername="postgresql+asyncpg",
)

# Supabase's transaction pooler uses port 6543. Serverless functions should not
# keep a second client-side pool in front of it, and asyncpg's prepared statement
# cache must be disabled for transaction-pooling mode.
uses_transaction_pooler = database_url.port == 6543

connect_args: dict[str, object] = {
    "ssl": settings.database_ssl_mode,
    "timeout": settings.database_timeout_seconds,
}

if uses_transaction_pooler:
    connect_args["statement_cache_size"] = 0

engine_kwargs: dict[str, object] = {
    "echo": settings.sql_echo,
    "pool_pre_ping": True,
    "connect_args": connect_args,
}

if uses_transaction_pooler:
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs["pool_size"] = settings.database_pool_size
    engine_kwargs["max_overflow"] = settings.database_max_overflow

engine = create_async_engine(
    database_url,
    **engine_kwargs,
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
