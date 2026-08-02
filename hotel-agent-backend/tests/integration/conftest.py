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
