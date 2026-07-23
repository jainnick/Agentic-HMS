import asyncio
from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientError

from app.core.config import Settings, get_settings

# Only asymmetric algorithms supported by this backend are allowed.
#
# Do not derive this list from the incoming JWT header.
ALLOWED_JWT_ALGORITHMS = ["ES256", "RS256"]


class AuthConfigurationError(RuntimeError):
    """Raised when required authentication settings are missing."""


class TokenValidationError(ValueError):
    """Raised when a supplied access token cannot be trusted."""


def resolve_auth_configuration(
    settings: Settings,
) -> tuple[str, str, str, int]:
    """Resolve audience, issuer, JWKS URL, and clock leeway."""

    supabase_url = (settings.supabase_url or "").strip().rstrip("/")

    if not supabase_url:
        raise AuthConfigurationError(
            "SUPABASE_URL is not configured.",
        )

    audience = settings.supabase_jwt_audience.strip()

    if not audience:
        raise AuthConfigurationError(
            "SUPABASE_JWT_AUDIENCE is not configured.",
        )

    issuer = (
        settings.supabase_jwt_issuer.strip().rstrip("/")
        if settings.supabase_jwt_issuer
        else f"{supabase_url}/auth/v1"
    )

    jwks_url = (
        settings.supabase_jwks_url.strip()
        if settings.supabase_jwks_url
        else f"{issuer}/.well-known/jwks.json"
    )

    return (
        audience,
        issuer,
        jwks_url,
        settings.supabase_jwt_leeway_seconds,
    )


@lru_cache(maxsize=4)
def get_jwks_client(
    jwks_url: str,
) -> PyJWKClient:
    """Create and cache a JWKS client for a Supabase project."""

    return PyJWKClient(
        jwks_url,
        cache_keys=True,
    )


def decode_access_token_sync(
    token: str,
) -> dict[str, Any]:
    """Synchronously verify a Supabase access token."""

    if not token.strip():
        raise TokenValidationError(
            "Access token is empty.",
        )

    settings = get_settings()

    audience, issuer, jwks_url, leeway = resolve_auth_configuration(
        settings,
    )

    try:
        jwks_client = get_jwks_client(jwks_url)

        # PyJWT reads the JWT header, obtains the key ID (kid), downloads the
        # matching public key from Supabase JWKS, and returns that signing key.
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        claims = jwt.decode(
            jwt=token,
            key=signing_key.key,
            algorithms=ALLOWED_JWT_ALGORITHMS,
            audience=audience,
            issuer=issuer,
            leeway=leeway,
            options={
                "require": [
                    "exp",
                    "iss",
                    "aud",
                    "sub",
                ],
            },
        )

    except (InvalidTokenError, PyJWKClientError) as exc:
        raise TokenValidationError(
            "Access token is invalid or expired.",
        ) from exc

    if not isinstance(claims, dict):
        raise TokenValidationError(
            "Access token claims are invalid.",
        )

    return claims


async def decode_access_token(
    token: str,
) -> dict[str, Any]:
    """Verify a Supabase access token without blocking FastAPI's event loop."""

    return await asyncio.to_thread(
        decode_access_token_sync,
        token,
    )
