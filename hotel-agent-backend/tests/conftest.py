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