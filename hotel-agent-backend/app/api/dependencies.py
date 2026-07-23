from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from app.core.security import (
    AuthConfigurationError,
    TokenValidationError,
    decode_access_token,
)
from app.modules.identity.schemas import CurrentUser
from app.modules.identity.service import (
    InvalidIdentityClaimsError,
    create_current_user,
)

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="Supabase access token",
)


def authentication_required_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


def invalid_token_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token.",
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> CurrentUser:
    """Validate a Bearer token and return the authenticated user."""

    if credentials is None:
        raise authentication_required_error()

    if credentials.scheme.lower() != "bearer":
        raise authentication_required_error()

    try:
        claims = await decode_access_token(
            credentials.credentials,
        )

        return create_current_user(claims)

    except AuthConfigurationError as exc:
        # This is a server configuration problem, not a user authentication
        # failure, so return 503 instead of 401.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is not configured.",
        ) from exc

    except (
        TokenValidationError,
        InvalidIdentityClaimsError,
    ) as exc:
        raise invalid_token_error() from exc


CurrentUserDependency = Annotated[
    CurrentUser,
    Depends(get_current_user),
]
