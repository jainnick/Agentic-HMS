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
