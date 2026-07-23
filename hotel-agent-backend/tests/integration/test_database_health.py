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
