import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tenancy.enums import (
    OrganizationRole,
    PropertyRole,
)
from app.modules.tenancy.models import (
    Organization,
    OrganizationMembership,
    Property,
    PropertyMembership,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="Set RUN_INTEGRATION_TESTS=1 to run Supabase integration tests.",
    ),
]


def unique_value(prefix: str) -> str:
    """Create a unique value to avoid collisions with previous test runs."""

    return f"{prefix}-{uuid4().hex[:12]}"


async def create_organization(
    session: AsyncSession,
    *,
    name: str | None = None,
    slug: str | None = None,
) -> Organization:
    organization = Organization(
        name=name or "Integration Test Organization",
        slug=slug or unique_value("test-organization"),
    )

    session.add(organization)
    await session.flush()

    return organization


async def create_property(
    session: AsyncSession,
    *,
    organization_id: UUID,
    code: str | None = None,
    created_by: UUID | None = None,
) -> Property:
    property_ = Property(
        organization_id=organization_id,
        name="Integration Test Property",
        code=code or unique_value("property"),
        timezone="Asia/Kolkata",
        currency="INR",
        created_by=created_by or uuid4(),
    )

    session.add(property_)
    await session.flush()

    return property_


async def create_organization_membership(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID | None = None,
    role: OrganizationRole = OrganizationRole.ORGANIZATION_OWNER,
    created_by: UUID | None = None,
) -> OrganizationMembership:
    membership = OrganizationMembership(
        organization_id=organization_id,
        user_id=user_id or uuid4(),
        role=role,
        created_by=created_by or uuid4(),
    )

    session.add(membership)
    await session.flush()

    return membership


async def create_property_membership(
    session: AsyncSession,
    *,
    organization_id: UUID,
    property_id: UUID,
    user_id: UUID | None = None,
    role: PropertyRole = PropertyRole.PROPERTY_MANAGER,
    created_by: UUID | None = None,
) -> PropertyMembership:
    membership = PropertyMembership(
        organization_id=organization_id,
        property_id=property_id,
        user_id=user_id or uuid4(),
        role=role,
        created_by=created_by or uuid4(),
    )

    session.add(membership)
    await session.flush()

    return membership


async def test_organization_can_be_created(
    db_session: AsyncSession,
) -> None:
    organization = await create_organization(db_session)

    assert organization.id is not None
    assert organization.name == "Integration Test Organization"
    assert organization.slug.startswith("test-organization-")


async def test_property_can_belong_to_organization(
    db_session: AsyncSession,
) -> None:
    organization = await create_organization(db_session)

    property_ = await create_property(
        db_session,
        organization_id=organization.id,
    )

    assert property_.id is not None
    assert property_.organization_id == organization.id
    assert property_.timezone == "Asia/Kolkata"
    assert property_.currency == "INR"


async def test_duplicate_organization_slug_is_rejected(
    db_session: AsyncSession,
) -> None:
    duplicate_slug = unique_value("duplicate-slug")

    await create_organization(
        db_session,
        name="Organization One",
        slug=duplicate_slug,
    )

    duplicate_organization = Organization(
        name="Organization Two",
        slug=duplicate_slug,
    )

    db_session.add(duplicate_organization)

    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()


async def test_duplicate_property_code_in_same_organization_is_rejected(
    db_session: AsyncSession,
) -> None:
    organization = await create_organization(db_session)
    duplicate_code = unique_value("hotel")

    await create_property(
        db_session,
        organization_id=organization.id,
        code=duplicate_code,
    )

    duplicate_property = Property(
        organization_id=organization.id,
        name="Duplicate Property",
        code=duplicate_code,
        timezone="Asia/Kolkata",
        currency="INR",
        created_by=uuid4(),
    )

    db_session.add(duplicate_property)

    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()


async def test_same_property_code_in_different_organizations_is_allowed(
    db_session: AsyncSession,
) -> None:
    organization_a = await create_organization(
        db_session,
        name="Organization A",
    )
    organization_b = await create_organization(
        db_session,
        name="Organization B",
    )

    shared_code = unique_value("shared-hotel")

    property_a = await create_property(
        db_session,
        organization_id=organization_a.id,
        code=shared_code,
    )
    property_b = await create_property(
        db_session,
        organization_id=organization_b.id,
        code=shared_code,
    )

    assert property_a.code == property_b.code
    assert property_a.organization_id != property_b.organization_id


async def test_duplicate_organization_membership_is_rejected(
    db_session: AsyncSession,
) -> None:
    organization = await create_organization(db_session)
    user_id = uuid4()

    await create_organization_membership(
        db_session,
        organization_id=organization.id,
        user_id=user_id,
    )

    duplicate_membership = OrganizationMembership(
        organization_id=organization.id,
        user_id=user_id,
        role=OrganizationRole.VIEWER,
        created_by=uuid4(),
    )

    db_session.add(duplicate_membership)

    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()


async def test_duplicate_property_membership_is_rejected(
    db_session: AsyncSession,
) -> None:
    organization = await create_organization(db_session)

    property_ = await create_property(
        db_session,
        organization_id=organization.id,
    )

    user_id = uuid4()

    await create_property_membership(
        db_session,
        organization_id=organization.id,
        property_id=property_.id,
        user_id=user_id,
    )

    duplicate_membership = PropertyMembership(
        organization_id=organization.id,
        property_id=property_.id,
        user_id=user_id,
        role=PropertyRole.VIEWER,
        created_by=uuid4(),
    )

    db_session.add(duplicate_membership)

    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()


async def test_property_membership_cannot_mix_organizations(
    db_session: AsyncSession,
) -> None:
    organization_a = await create_organization(
        db_session,
        name="Organization A",
    )
    organization_b = await create_organization(
        db_session,
        name="Organization B",
    )

    property_b = await create_property(
        db_session,
        organization_id=organization_b.id,
    )

    invalid_membership = PropertyMembership(
        organization_id=organization_a.id,
        property_id=property_b.id,
        user_id=uuid4(),
        role=PropertyRole.PROPERTY_MANAGER,
        created_by=uuid4(),
    )

    db_session.add(invalid_membership)

    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()


async def test_deleting_organization_cascades_dependent_records(
    db_session: AsyncSession,
) -> None:
    organization = await create_organization(db_session)

    property_ = await create_property(
        db_session,
        organization_id=organization.id,
    )

    await create_organization_membership(
        db_session,
        organization_id=organization.id,
    )

    await create_property_membership(
        db_session,
        organization_id=organization.id,
        property_id=property_.id,
    )

    await db_session.execute(
        delete(Organization).where(
            Organization.id == organization.id,
        )
    )
    await db_session.flush()

    property_count = await db_session.scalar(
        select(func.count())
        .select_from(Property)
        .where(Property.organization_id == organization.id)
    )

    organization_membership_count = await db_session.scalar(
        select(func.count())
        .select_from(OrganizationMembership)
        .where(
            OrganizationMembership.organization_id == organization.id,
        )
    )

    property_membership_count = await db_session.scalar(
        select(func.count())
        .select_from(PropertyMembership)
        .where(
            PropertyMembership.organization_id == organization.id,
        )
    )

    assert property_count == 0
    assert organization_membership_count == 0
    assert property_membership_count == 0
