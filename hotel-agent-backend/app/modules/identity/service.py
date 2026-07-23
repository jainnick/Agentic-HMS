from collections.abc import Mapping
from typing import Any
from uuid import UUID

from app.modules.identity.schemas import CurrentUser


class InvalidIdentityClaimsError(ValueError):
    """Raised when trusted JWT claims cannot identify a valid user."""


def create_current_user(
    claims: Mapping[str, Any],
) -> CurrentUser:
    """Create an application user from validated Supabase JWT claims."""

    subject = claims.get("sub")

    if not isinstance(subject, str) or not subject.strip():
        raise InvalidIdentityClaimsError(
            "JWT subject claim is missing.",
        )

    try:
        user_id = UUID(subject)
    except ValueError as exc:
        raise InvalidIdentityClaimsError(
            "JWT subject is not a valid UUID.",
        ) from exc

    auth_role = claims.get("role")

    if not isinstance(auth_role, str) or not auth_role.strip():
        raise InvalidIdentityClaimsError(
            "JWT role claim is missing.",
        )

    email_claim = claims.get("email")

    email = email_claim if isinstance(email_claim, str) else None

    return CurrentUser(
        id=user_id,
        email=email,
        auth_role=auth_role,
    )
