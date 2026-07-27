import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.schemas import CurrentUser
from app.modules.tenancy.enums import (
    LifecycleStatus,
    OrganizationRole,
    PropertyRole,
)
from app.modules.tenancy.models import (
    Organization,
    OrganizationMembership,
    Property,
    PropertyMembership,
)
from app.modules.tenancy.service import (
    TenantAccessDeniedError,
    TenantResourceNotFoundError,
    resolve_tenant_context,
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
        email="tenant-user@example.com",
        auth_role="authenticated",
    )


async def create_organization(
    session: AsyncSession,
    *,
    status: LifecycleStatus = LifecycleStatus.ACTIVE,
) -> Organization:
    organization = Organization(
        name="Tenant Test Organization",
        slug=f"tenant-{uuid4().hex}",
        status=status,
    )

    session.add(
        organization,
    )
    await session.flush()

    return organization


async def create_property(
    session: AsyncSession,
    *,
    organization_id: UUID,
    status: LifecycleStatus = LifecycleStatus.ACTIVE,
) -> Property:
    property_ = Property(
        organization_id=organization_id,
        name="Tenant Test Property",
        code=f"PROP-{uuid4().hex[:8]}",
        timezone="Asia/Kolkata",
        currency="INR",
        status=status,
        created_by=uuid4(),
    )

    session.add(
        property_,
    )
    await session.flush()

    return property_


async def create_organization_membership(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    role: OrganizationRole = OrganizationRole.ORGANIZATION_OWNER,
    status: LifecycleStatus = LifecycleStatus.ACTIVE,
) -> OrganizationMembership:
    membership = OrganizationMembership(
        organization_id=organization_id,
        user_id=user_id,
        role=role,
        status=status,
        created_by=user_id,
    )

    session.add(
        membership,
    )
    await session.flush()

    return membership


async def create_property_membership(
    session: AsyncSession,
    *,
    organization_id: UUID,
    property_id: UUID,
    user_id: UUID,
    role: PropertyRole = PropertyRole.PROPERTY_MANAGER,
    status: LifecycleStatus = LifecycleStatus.ACTIVE,
) -> PropertyMembership:
    membership = PropertyMembership(
        organization_id=organization_id,
        property_id=property_id,
        user_id=user_id,
        role=role,
        status=status,
        created_by=user_id,
    )

    session.add(
        membership,
    )
    await session.flush()

    return membership


async def test_organization_owner_can_access_organization(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()
    organization = await create_organization(db_session)

    await create_organization_membership(
        db_session,
        organization_id=organization.id,
        user_id=current_user.id,
    )

    tenant_context = await resolve_tenant_context(
        db_session,
        current_user=current_user,
        organization_id=organization.id,
    )

    assert tenant_context.user_id == current_user.id
    assert tenant_context.organization_id == organization.id
    assert tenant_context.property_id is None
    assert tenant_context.organization_role == OrganizationRole.ORGANIZATION_OWNER
    assert tenant_context.property_role is None


async def test_organization_owner_can_access_property(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()
    organization = await create_organization(db_session)

    property_ = await create_property(
        db_session,
        organization_id=organization.id,
    )

    await create_organization_membership(
        db_session,
        organization_id=organization.id,
        user_id=current_user.id,
    )

    tenant_context = await resolve_tenant_context(
        db_session,
        current_user=current_user,
        organization_id=organization.id,
        property_id=property_.id,
    )

    assert tenant_context.organization_id == organization.id
    assert tenant_context.property_id == property_.id
    assert tenant_context.organization_role == OrganizationRole.ORGANIZATION_OWNER


async def test_property_manager_can_access_assigned_property(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()
    organization = await create_organization(db_session)

    property_ = await create_property(
        db_session,
        organization_id=organization.id,
    )

    await create_property_membership(
        db_session,
        organization_id=organization.id,
        property_id=property_.id,
        user_id=current_user.id,
    )

    tenant_context = await resolve_tenant_context(
        db_session,
        current_user=current_user,
        organization_id=organization.id,
        property_id=property_.id,
    )

    assert tenant_context.organization_role is None
    assert tenant_context.property_role == PropertyRole.PROPERTY_MANAGER
    assert tenant_context.property_id == property_.id


async def test_property_manager_cannot_access_another_property(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()
    organization = await create_organization(db_session)

    assigned_property = await create_property(
        db_session,
        organization_id=organization.id,
    )

    other_property = await create_property(
        db_session,
        organization_id=organization.id,
    )

    await create_property_membership(
        db_session,
        organization_id=organization.id,
        property_id=assigned_property.id,
        user_id=current_user.id,
    )

    with pytest.raises(
        TenantAccessDeniedError,
        match="does not have access to this property",
    ):
        await resolve_tenant_context(
            db_session,
            current_user=current_user,
            organization_id=organization.id,
            property_id=other_property.id,
        )


async def test_inactive_organization_membership_is_rejected(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()
    organization = await create_organization(db_session)

    await create_organization_membership(
        db_session,
        organization_id=organization.id,
        user_id=current_user.id,
        status=LifecycleStatus.INACTIVE,
    )

    with pytest.raises(TenantAccessDeniedError):
        await resolve_tenant_context(
            db_session,
            current_user=current_user,
            organization_id=organization.id,
        )


async def test_inactive_property_membership_is_rejected(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()
    organization = await create_organization(db_session)

    property_ = await create_property(
        db_session,
        organization_id=organization.id,
    )

    await create_property_membership(
        db_session,
        organization_id=organization.id,
        property_id=property_.id,
        user_id=current_user.id,
        status=LifecycleStatus.INACTIVE,
    )

    with pytest.raises(TenantAccessDeniedError):
        await resolve_tenant_context(
            db_session,
            current_user=current_user,
            organization_id=organization.id,
            property_id=property_.id,
        )


async def test_property_from_another_organization_is_rejected(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()

    organization_a = await create_organization(db_session)
    organization_b = await create_organization(db_session)

    property_b = await create_property(
        db_session,
        organization_id=organization_b.id,
    )

    await create_organization_membership(
        db_session,
        organization_id=organization_a.id,
        user_id=current_user.id,
    )

    with pytest.raises(TenantResourceNotFoundError):
        await resolve_tenant_context(
            db_session,
            current_user=current_user,
            organization_id=organization_a.id,
            property_id=property_b.id,
        )


async def test_unknown_organization_is_rejected(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()

    with pytest.raises(TenantResourceNotFoundError):
        await resolve_tenant_context(
            db_session,
            current_user=current_user,
            organization_id=uuid4(),
        )


async def test_known_organization_without_membership_is_rejected(
    db_session: AsyncSession,
) -> None:
    current_user = create_test_user()
    organization = await create_organization(db_session)

    with pytest.raises(TenantAccessDeniedError):
        await resolve_tenant_context(
            db_session,
            current_user=current_user,
            organization_id=organization.id,
        )
