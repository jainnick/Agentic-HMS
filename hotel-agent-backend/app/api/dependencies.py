from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
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
from app.modules.tenancy.context import TenantContext
from app.modules.tenancy.service import (
    TenantAccessDeniedError,
    TenantResourceNotFoundError,
    resolve_tenant_context,
)

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="Supabase access token",
)


def authentication_required_error() -> HTTPException:
    """Return a standard response when authentication is missing."""

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


def invalid_token_error() -> HTTPException:
    """Return a standard response when a token cannot be trusted."""

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
    """
    Validate a Supabase access token and return the authenticated user.

    This dependency identifies the user only. Tenant access is resolved
    separately through get_tenant_context().
    """

    if credentials is None:
        raise authentication_required_error()

    if credentials.scheme.lower() != "bearer":
        raise authentication_required_error()

    try:
        claims = await decode_access_token(
            credentials.credentials,
        )

        return create_current_user(
            claims,
        )

    except AuthConfigurationError as exc:
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


DatabaseSessionDependency = Annotated[
    AsyncSession,
    Depends(get_db_session),
]


async def get_tenant_context(
    current_user: CurrentUserDependency,
    session: DatabaseSessionDependency,
    organization_id: Annotated[
        UUID,
        Header(
            alias="X-Organization-ID",
            description="Organization selected in the Agentic HMS portal.",
        ),
    ],
    property_id: Annotated[
        UUID | None,
        Header(
            alias="X-Property-ID",
            description="Optional hotel property selected in the portal.",
        ),
    ] = None,
) -> TenantContext:
    """
    Verify the organization and optional property selected by the user.

    Header values are treated as requested values only. The tenancy service
    verifies the resources and memberships before returning TenantContext.
    """

    try:
        return await resolve_tenant_context(
            session,
            current_user=current_user,
            organization_id=organization_id,
            property_id=property_id,
        )

    except TenantResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested tenant was not found.",
        ) from exc

    except TenantAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to the requested tenant.",
        ) from exc


TenantContextDependency = Annotated[
    TenantContext,
    Depends(get_tenant_context),
]
