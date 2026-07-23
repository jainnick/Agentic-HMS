from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import TokenValidationError

AUTH_ME_URL = "/api/v1/auth/me"


def test_auth_me_requires_token(
    client: TestClient,
) -> None:
    response = client.get(AUTH_ME_URL)

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication required.",
    }

    assert response.headers["www-authenticate"] == "Bearer"


def test_auth_me_returns_authenticated_user(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()

    async def valid_token_decoder(
        token: str,
    ) -> dict[str, object]:
        assert token == "valid-test-token"

        return {
            "sub": str(user_id),
            "email": "manager@example.com",
            "role": "authenticated",
        }

    monkeypatch.setattr(
        "app.api.dependencies.decode_access_token",
        valid_token_decoder,
    )

    response = client.get(
        AUTH_ME_URL,
        headers={
            "Authorization": "Bearer valid-test-token",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(user_id),
        "email": "manager@example.com",
        "auth_role": "authenticated",
    }


def test_auth_me_rejects_invalid_token(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def invalid_token_decoder(
        _: str,
    ) -> dict[str, object]:
        raise TokenValidationError(
            "Token validation failed.",
        )

    monkeypatch.setattr(
        "app.api.dependencies.decode_access_token",
        invalid_token_decoder,
    )

    response = client.get(
        AUTH_ME_URL,
        headers={
            "Authorization": "Bearer invalid-test-token",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid authentication token.",
    }


def test_auth_me_rejects_malformed_user_claims(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def malformed_claims_decoder(
        _: str,
    ) -> dict[str, object]:
        return {
            "sub": "not-a-uuid",
            "role": "authenticated",
        }

    monkeypatch.setattr(
        "app.api.dependencies.decode_access_token",
        malformed_claims_decoder,
    )

    response = client.get(
        AUTH_ME_URL,
        headers={
            "Authorization": "Bearer malformed-user-token",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid authentication token.",
    }
