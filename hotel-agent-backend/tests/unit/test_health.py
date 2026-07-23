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
