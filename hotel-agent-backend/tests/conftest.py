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
