from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import (
    CurrentUserDependency,
    DatabaseSessionDependency,
)
from app.modules.onboarding.schemas import (
    OnboardingStatusResponse,
    OrganizationCreateRequest,
    OrganizationCreateResponse,
    PropertyCreateRequest,
    PropertyCreateResponse,
)
from app.modules.onboarding.service import (
    OnboardingAccessDeniedError,
    OnboardingConflictError,
    create_first_organization,
    create_first_property,
    get_onboarding_status,
)

router = APIRouter(
    prefix="/onboarding",
    tags=["Onboarding"],
)


@router.get(
    "/status",
    response_model=OnboardingStatusResponse,
)
async def read_onboarding_status(
    current_user: CurrentUserDependency,
    session: DatabaseSessionDependency,
) -> OnboardingStatusResponse:
    """Return the next onboarding step for the authenticated user."""

    return await get_onboarding_status(
        session,
        current_user=current_user,
    )


@router.post(
    "/organization",
    response_model=OrganizationCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_onboarding_organization(
    payload: OrganizationCreateRequest,
    current_user: CurrentUserDependency,
    session: DatabaseSessionDependency,
) -> OrganizationCreateResponse:
    """Create the user's first organization and owner membership."""

    try:
        organization = await create_first_organization(
            session,
            current_user=current_user,
            payload=payload,
        )

    except OnboardingConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return OrganizationCreateResponse.model_validate(
        organization,
    )


@router.post(
    "/property",
    response_model=PropertyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_onboarding_property(
    payload: PropertyCreateRequest,
    current_user: CurrentUserDependency,
    session: DatabaseSessionDependency,
) -> PropertyCreateResponse:
    """Create the first property under the user's owned organization."""

    try:
        property_ = await create_first_property(
            session,
            current_user=current_user,
            payload=payload,
        )

    except OnboardingAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except OnboardingConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return PropertyCreateResponse.model_validate(
        property_,
    )
