import os
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.schemas import CurrentUser
from app.modules.onboarding.schemas import (
    OnboardingStep,
    OrganizationCreateRequest,
    PropertyCreateRequest,
)
from app.modules.onboarding.service import (
    OnboardingAccessDeniedError,
    OnboardingConflictError,
    create_first_organization,
    create_first_property,
    get_onboarding_status,
)
from app.modules.tenancy.enums import (
    LifecycleStatus,
    OrganizationRole,
)
from app.modules.tenancy.models import (
    Organization,
    OrganizationMembership,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="Set RUN_INTEGRATION_TESTS=1 to run Supabase integration tests.",
    ),
]


def create_test_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        email="integration-user@example.com",
        auth_role="authenticated",
    )


def create_organization_payload() -> OrganizationCreateRequest:
    return OrganizationCreateRequest(
        name=f"Integration Hotels {uuid4().hex[:8]}",
    )


def create_property_payload(
    *,
    code: str | None = None,
) -> PropertyCreateRequest:
    return PropertyCreateRequest(
        name="Integration Hotel Delhi",
        code=code or f"DEL-{uuid4().hex[:8]}",
        timezone="Asia/Kolkata",
        currency="INR",
    )


async def test_new_user_must_create_organization(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()

    onboarding_status = await get_onboarding_status(
        db_session,
        current_user=current_user,
    )

    assert onboarding_status.has_organization is False
    assert onboarding_status.has_property is False
    assert onboarding_status.next_step == OnboardingStep.CREATE_ORGANIZATION
    assert onboarding_status.organization_id is None
    assert onboarding_status.property_id is None


async def test_creating_organization_also_creates_owner_membership(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()

    organization = await create_first_organization(
        db_session,
        current_user=current_user,
        payload=create_organization_payload(),
    )

    membership = await db_session.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization.id,
            OrganizationMembership.user_id == current_user.id,
        )
    )

    assert membership is not None
    assert membership.organization_id == organization.id
    assert membership.user_id == current_user.id
    assert membership.role == OrganizationRole.ORGANIZATION_OWNER
    assert membership.status == LifecycleStatus.ACTIVE
    assert membership.created_by == current_user.id


async def test_organization_owner_must_create_property_next(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()

    organization = await create_first_organization(
        db_session,
        current_user=current_user,
        payload=create_organization_payload(),
    )

    onboarding_status = await get_onboarding_status(
        db_session,
        current_user=current_user,
    )

    assert onboarding_status.has_organization is True
    assert onboarding_status.has_property is False
    assert onboarding_status.next_step == OnboardingStep.CREATE_PROPERTY
    assert onboarding_status.organization_id == organization.id
    assert onboarding_status.property_id is None


async def test_creating_first_property_completes_onboarding(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()

    organization = await create_first_organization(
        db_session,
        current_user=current_user,
        payload=create_organization_payload(),
    )

    property_ = await create_first_property(
        db_session,
        current_user=current_user,
        payload=create_property_payload(),
    )

    onboarding_status = await get_onboarding_status(
        db_session,
        current_user=current_user,
    )

    assert property_.organization_id == organization.id
    assert property_.created_by == current_user.id

    assert onboarding_status.has_organization is True
    assert onboarding_status.has_property is True
    assert onboarding_status.next_step == OnboardingStep.COMPLETED
    assert onboarding_status.organization_id == organization.id
    assert onboarding_status.property_id == property_.id


async def test_user_cannot_create_second_initial_organization(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()

    await create_first_organization(
        db_session,
        current_user=current_user,
        payload=create_organization_payload(),
    )

    with pytest.raises(
        OnboardingConflictError,
        match="already belongs to an organization",
    ):
        await create_first_organization(
            db_session,
            current_user=current_user,
            payload=create_organization_payload(),
        )


async def test_non_owner_cannot_create_initial_property(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()

    organization = Organization(
        name="Viewer Organization",
        slug=f"viewer-{uuid4().hex}",
    )

    db_session.add(
        organization,
    )
    await db_session.flush()

    membership = OrganizationMembership(
        organization_id=organization.id,
        user_id=current_user.id,
        role=OrganizationRole.VIEWER,
        status=LifecycleStatus.ACTIVE,
        created_by=current_user.id,
    )

    db_session.add(
        membership,
    )
    await db_session.flush()

    with pytest.raises(
        OnboardingAccessDeniedError,
        match="organization-owner membership is required",
    ):
        await create_first_property(
            db_session,
            current_user=current_user,
            payload=create_property_payload(),
        )


async def test_organization_cannot_create_second_initial_property(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()

    await create_first_organization(
        db_session,
        current_user=current_user,
        payload=create_organization_payload(),
    )

    await create_first_property(
        db_session,
        current_user=current_user,
        payload=create_property_payload(),
    )

    with pytest.raises(
        OnboardingConflictError,
        match="already has a property",
    ):
        await create_first_property(
            db_session,
            current_user=current_user,
            payload=create_property_payload(),
        )
