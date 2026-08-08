from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
    func,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.api.dependencies import (
    DatabaseSessionDependency,
    TenantContextDependency,
)
from app.db.base import Base
from app.modules.tenancy.context import TenantContext
from app.modules.tenancy.service import (
    TenantAccessDeniedError,
    require_property_management_access,
)

# ---------------------------------------------------------------------------
# Supported assistant capabilities
# ---------------------------------------------------------------------------


class PropertyToolName(StrEnum):
    KNOWLEDGE_SEARCH = "knowledge_search"
    ROOM_AVAILABILITY = "room_availability"
    ROOM_BOOKING = "room_booking"


# These are application defaults.
#
# We do not create one database row for every tool/property combination.
# A database row is created only when an administrator changes a setting.
DEFAULT_TOOL_STATES: dict[PropertyToolName, bool] = {
    PropertyToolName.KNOWLEDGE_SEARCH: True,
    PropertyToolName.ROOM_AVAILABILITY: False,
    PropertyToolName.ROOM_BOOKING: False,
}


# ---------------------------------------------------------------------------
# Database model
# ---------------------------------------------------------------------------


class PropertyTool(Base):
    """
    Property-specific override for an assistant capability.

    No row means the application's default state is used.
    """

    __tablename__ = "property_tools"

    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "property_id"],
            ["properties.organization_id", "properties.id"],
            name="fk_property_tools_property_organization",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "property_id",
            "tool_name",
            name="uq_property_tools_property_id_tool_name",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )

    property_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )

    tool_name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    configuration: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


# ---------------------------------------------------------------------------
# API schemas
# ---------------------------------------------------------------------------


class PropertyToolUpdate(BaseModel):
    enabled: bool

    configuration: dict[str, Any] = Field(
        default_factory=dict,
    )


class PropertyToolResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    tool_name: PropertyToolName
    enabled: bool
    configuration: dict[str, Any]


# ---------------------------------------------------------------------------
# Small service functions
# ---------------------------------------------------------------------------


def require_property_tool_management(
    tenant_context: TenantContext,
) -> UUID:
    """
    Ensure the request targets a property and the user may manage it.

    Returns the verified property ID so callers do not repeat the same checks.
    """

    if tenant_context.property_id is None:
        raise ValueError(
            "A property must be selected.",
        )

    require_property_management_access(
        tenant_context,
    )

    return tenant_context.property_id


async def get_property_tool_overrides(
    session: AsyncSession,
    *,
    property_id: UUID,
) -> dict[PropertyToolName, PropertyTool]:
    """Return explicitly stored tool settings for one property."""

    result = await session.scalars(
        select(PropertyTool).where(
            PropertyTool.property_id == property_id,
        )
    )

    overrides: dict[PropertyToolName, PropertyTool] = {}

    for row in result:
        try:
            tool_name = PropertyToolName(row.tool_name)
        except ValueError:
            # Ignore old/unknown values rather than breaking the whole endpoint.
            continue

        overrides[tool_name] = row

    return overrides


async def list_property_tools(
    session: AsyncSession,
    *,
    property_id: UUID,
) -> list[PropertyToolResponse]:
    """
    Merge application defaults with property-specific overrides.
    """

    overrides = await get_property_tool_overrides(
        session,
        property_id=property_id,
    )

    return [
        PropertyToolResponse(
            tool_name=tool_name,
            enabled=(overrides[tool_name].enabled if tool_name in overrides else default_enabled),
            configuration=(overrides[tool_name].configuration if tool_name in overrides else {}),
        )
        for tool_name, default_enabled in DEFAULT_TOOL_STATES.items()
    ]


async def set_property_tool(
    session: AsyncSession,
    *,
    organization_id: UUID,
    property_id: UUID,
    tool_name: PropertyToolName,
    payload: PropertyToolUpdate,
) -> PropertyToolResponse:
    """
    Create or update one property-specific tool override.

    PostgreSQL ON CONFLICT performs this atomically:
    - no existing property/tool row -> INSERT
    - existing property/tool row -> UPDATE
    """

    statement = (
        insert(PropertyTool)
        .values(
            organization_id=organization_id,
            property_id=property_id,
            tool_name=tool_name.value,
            enabled=payload.enabled,
            configuration=payload.configuration,
        )
        .on_conflict_do_update(
            constraint="uq_property_tools_property_id_tool_name",
            set_={
                "enabled": payload.enabled,
                "configuration": payload.configuration,
                "updated_at": func.now(),
            },
        )
        .returning(PropertyTool)
    )

    property_tool = await session.scalar(statement)

    if property_tool is None:
        raise RuntimeError(
            "Property tool configuration could not be saved.",
        )

    await session.commit()

    return PropertyToolResponse.model_validate(
        property_tool,
    )

async def is_property_tool_enabled(
    session: AsyncSession,
    *,
    property_id: UUID,
    tool_name: PropertyToolName,
) -> bool:
    """
    Resolve the effective enabled state for one tool.

    This function will later be reused by the assistant before exposing or
    executing property-specific tools.
    """

    enabled = await session.scalar(
        select(PropertyTool.enabled).where(
            PropertyTool.property_id == property_id,
            PropertyTool.tool_name == tool_name.value,
        )
    )

    if enabled is not None:
        return enabled

    return DEFAULT_TOOL_STATES[tool_name]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


router = APIRouter(
    prefix="/admin/property-tools",
    tags=["Property Tools"],
)


@router.get(
    "",
    response_model=list[PropertyToolResponse],
)
async def get_property_tools(
    tenant_context: TenantContextDependency,
    session: DatabaseSessionDependency,
) -> list[PropertyToolResponse]:
    """
    Return the effective capability configuration for the selected property.
    """

    try:
        property_id = require_property_tool_management(
            tenant_context,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except TenantAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    return await list_property_tools(
        session,
        property_id=property_id,
    )


@router.put(
    "/{tool_name}",
    response_model=PropertyToolResponse,
)
async def update_property_tool(
    tool_name: PropertyToolName,
    payload: PropertyToolUpdate,
    tenant_context: TenantContextDependency,
    session: DatabaseSessionDependency,
) -> PropertyToolResponse:
    """
    Create or replace one property-specific tool configuration.
    """

    try:
        property_id = require_property_tool_management(
            tenant_context,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except TenantAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    return await set_property_tool(
        session,
        organization_id=tenant_context.organization_id,
        property_id=property_id,
        tool_name=tool_name,
        payload=payload,
    )
