import os
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.property_tools import (
    PropertyTool,
    PropertyToolName,
    PropertyToolUpdate,
    list_property_tools,
    set_property_tool,
)
from app.modules.tenancy.models import Organization, Property

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="Set RUN_INTEGRATION_TESTS=1 to run Supabase integration tests.",
    ),
]


async def create_property(
    session: AsyncSession,
) -> tuple[Organization, Property]:
    organization = Organization(
        name="Property Tools Test",
        slug=f"property-tools-{uuid4().hex}",
    )

    session.add(organization)
    await session.flush()

    property_ = Property(
        organization_id=organization.id,
        name="Property Tools Hotel",
        code=f"PT-{uuid4().hex[:8]}",
        timezone="Asia/Kolkata",
        currency="INR",
        created_by=uuid4(),
    )

    session.add(property_)
    await session.flush()

    return organization, property_


async def test_defaults_are_returned_without_database_rows(
    db_session: AsyncSession,
) -> None:
    _, property_ = await create_property(db_session)

    tools = await list_property_tools(
        db_session,
        property_id=property_.id,
    )

    states = {
        tool.tool_name: tool.enabled
        for tool in tools
    }

    assert states == {
        PropertyToolName.KNOWLEDGE_SEARCH: True,
        PropertyToolName.ROOM_AVAILABILITY: False,
        PropertyToolName.ROOM_BOOKING: False,
    }


async def test_property_tool_override_can_be_created(
    db_session: AsyncSession,
) -> None:
    organization, property_ = await create_property(db_session)

    result = await set_property_tool(
        db_session,
        organization_id=organization.id,
        property_id=property_.id,
        tool_name=PropertyToolName.ROOM_AVAILABILITY,
        payload=PropertyToolUpdate(
            enabled=True,
        ),
    )

    assert result.tool_name == PropertyToolName.ROOM_AVAILABILITY
    assert result.enabled is True


async def test_updating_tool_does_not_create_duplicate(
    db_session: AsyncSession,
) -> None:
    organization, property_ = await create_property(db_session)

    await set_property_tool(
        db_session,
        organization_id=organization.id,
        property_id=property_.id,
        tool_name=PropertyToolName.ROOM_AVAILABILITY,
        payload=PropertyToolUpdate(
            enabled=True,
        ),
    )

    await set_property_tool(
        db_session,
        organization_id=organization.id,
        property_id=property_.id,
        tool_name=PropertyToolName.ROOM_AVAILABILITY,
        payload=PropertyToolUpdate(
            enabled=False,
        ),
    )

    count = await db_session.scalar(
        select(func.count(PropertyTool.id)).where(
            PropertyTool.property_id == property_.id,
            PropertyTool.tool_name == PropertyToolName.ROOM_AVAILABILITY.value,
        )
    )

    assert count == 1


async def test_property_tool_overrides_are_property_scoped(
    db_session: AsyncSession,
) -> None:
    organization, property_a = await create_property(db_session)

    property_b = Property(
        organization_id=organization.id,
        name="Second Hotel",
        code=f"PT-{uuid4().hex[:8]}",
        timezone="Asia/Kolkata",
        currency="INR",
        created_by=uuid4(),
    )

    db_session.add(property_b)
    await db_session.flush()

    await set_property_tool(
        db_session,
        organization_id=organization.id,
        property_id=property_a.id,
        tool_name=PropertyToolName.ROOM_AVAILABILITY,
        payload=PropertyToolUpdate(
            enabled=True,
        ),
    )

    tools_b = await list_property_tools(
        db_session,
        property_id=property_b.id,
    )

    room_availability = next(
        tool
        for tool in tools_b
        if tool.tool_name == PropertyToolName.ROOM_AVAILABILITY
    )

    assert room_availability.enabled is False