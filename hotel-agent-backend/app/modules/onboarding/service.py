import re

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.schemas import CurrentUser
from app.modules.onboarding.schemas import (
    OnboardingStatusResponse,
    OnboardingStep,
    OrganizationCreateRequest,
    PropertyCreateRequest,
)
from app.modules.tenancy.enums import (
    LifecycleStatus,
    OrganizationRole,
)
from app.modules.tenancy.models import (
    Organization,
    OrganizationMembership,
    Property,
)


class OnboardingError(Exception):
    """Base error for onboarding failures."""


class OnboardingConflictError(OnboardingError):
    """Raised when onboarding would duplicate an existing resource."""


class OnboardingAccessDeniedError(OnboardingError):
    """Raised when the user cannot perform the requested onboarding step."""


def slugify(
    value: str,
) -> str:
    """Convert an organization name into a URL-friendly slug."""

    normalized = value.strip().lower()

    normalized = re.sub(
        r"[^a-z0-9]+",
        "-",
        normalized,
    )

    return normalized.strip("-") or "organization"


async def generate_unique_organization_slug(
    session: AsyncSession,
    *,
    organization_name: str,
) -> str:
    """Generate a slug that is unique across organizations."""

    base_slug = slugify(
        organization_name,
    )
    candidate = base_slug
    suffix = 2

    while await session.scalar(
        select(Organization.id).where(
            Organization.slug == candidate,
        )
    ):
        candidate = f"{base_slug}-{suffix}"
        suffix += 1

    return candidate


async def get_onboarding_status(
    session: AsyncSession,
    *,
    current_user: CurrentUser,
) -> OnboardingStatusResponse:
    """Determine the user's onboarding state from existing tenant data."""

    organization_membership = await session.execute(
        select(
            OrganizationMembership.organization_id,
        )
        .where(
            OrganizationMembership.user_id == current_user.id,
            OrganizationMembership.status == LifecycleStatus.ACTIVE,
        )
        .order_by(
            OrganizationMembership.created_at.asc(),
        )
        .limit(1)
    )

    organization_id = organization_membership.scalar_one_or_none()

    if organization_id is None:
        return OnboardingStatusResponse(
            has_organization=False,
            has_property=False,
            next_step=OnboardingStep.CREATE_ORGANIZATION,
        )

    property_id = await session.scalar(
        select(Property.id)
        .where(
            Property.organization_id == organization_id,
            Property.status == LifecycleStatus.ACTIVE,
        )
        .order_by(
            Property.created_at.asc(),
        )
        .limit(1)
    )

    if property_id is None:
        return OnboardingStatusResponse(
            has_organization=True,
            has_property=False,
            next_step=OnboardingStep.CREATE_PROPERTY,
            organization_id=organization_id,
        )

    return OnboardingStatusResponse(
        has_organization=True,
        has_property=True,
        next_step=OnboardingStep.COMPLETED,
        organization_id=organization_id,
        property_id=property_id,
    )


async def create_first_organization(
    session: AsyncSession,
    *,
    current_user: CurrentUser,
    payload: OrganizationCreateRequest,
) -> Organization:
    """
    Create the user's first organization and owner membership atomically.

    The authenticated user automatically becomes organization_owner.
    """

    existing_membership = await session.scalar(
        select(OrganizationMembership.id).where(
            OrganizationMembership.user_id == current_user.id,
            OrganizationMembership.status == LifecycleStatus.ACTIVE,
        )
    )

    if existing_membership is not None:
        raise OnboardingConflictError(
            "The user already belongs to an organization.",
        )

    slug = await generate_unique_organization_slug(
        session,
        organization_name=payload.name,
    )

    organization = Organization(
        name=payload.name,
        slug=slug,
    )

    try:
        session.add(
            organization,
        )
        await session.flush()

        owner_membership = OrganizationMembership(
            organization_id=organization.id,
            user_id=current_user.id,
            role=OrganizationRole.ORGANIZATION_OWNER,
            created_by=current_user.id,
        )

        session.add(
            owner_membership,
        )

        await session.commit()
        await session.refresh(
            organization,
        )

    except IntegrityError as exc:
        await session.rollback()

        raise OnboardingConflictError(
            "The organization could not be created because of a conflicting record.",
        ) from exc

    except Exception:
        await session.rollback()
        raise

    return organization


async def create_first_property(
    session: AsyncSession,
    *,
    current_user: CurrentUser,
    payload: PropertyCreateRequest,
) -> Property:
    """
    Create the first property under the user's owned organization.

    The organization ID and created_by value are derived from the authenticated
    user's active organization-owner membership.
    """

    organization_id = await session.scalar(
        select(
            OrganizationMembership.organization_id,
        ).where(
            OrganizationMembership.user_id == current_user.id,
            OrganizationMembership.role == OrganizationRole.ORGANIZATION_OWNER,
            OrganizationMembership.status == LifecycleStatus.ACTIVE,
        )
    )

    if organization_id is None:
        raise OnboardingAccessDeniedError(
            "An active organization-owner membership is required.",
        )

    existing_property_count = await session.scalar(
        select(
            func.count(Property.id),
        ).where(
            Property.organization_id == organization_id,
        )
    )

    if existing_property_count and existing_property_count > 0:
        raise OnboardingConflictError(
            "The organization already has a property.",
        )

    property_ = Property(
        organization_id=organization_id,
        name=payload.name,
        code=payload.code,
        timezone=payload.timezone,
        currency=payload.currency,
        created_by=current_user.id,
    )

    try:
        session.add(
            property_,
        )

        await session.commit()
        await session.refresh(
            property_,
        )

    except IntegrityError as exc:
        await session.rollback()

        raise OnboardingConflictError(
            "The property code is already used by this organization.",
        ) from exc

    except Exception:
        await session.rollback()
        raise

    return property_
