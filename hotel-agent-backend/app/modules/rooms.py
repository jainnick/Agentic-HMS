from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
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


class RoomType(Base):
    """One sellable room category for a hotel property."""

    __tablename__ = "room_types"

    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "property_id"],
            ["properties.organization_id", "properties.id"],
            name="fk_room_types_property_organization",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "property_id",
            "code",
            name="uq_room_types_property_id_code",
        ),
        UniqueConstraint(
            "organization_id",
            "property_id",
            "id",
            name="uq_room_types_organization_property_id",
        ),
        CheckConstraint(
            "char_length(btrim(code)) > 0",
            name="ck_room_types_code_not_blank",
        ),
        CheckConstraint(
            "char_length(btrim(name)) > 0",
            name="ck_room_types_name_not_blank",
        ),
        CheckConstraint(
            "total_rooms > 0",
            name="ck_room_types_total_rooms_positive",
        ),
        CheckConstraint(
            "max_adults > 0",
            name="ck_room_types_max_adults_positive",
        ),
        CheckConstraint(
            "max_children >= 0",
            name="ck_room_types_max_children_non_negative",
        ),
        CheckConstraint(
            "nightly_rate >= 0",
            name="ck_room_types_nightly_rate_non_negative",
        ),
        CheckConstraint(
            "char_length(currency) = 3 AND currency = upper(currency)",
            name="ck_room_types_currency_code",
        ),
        Index(
            "ix_room_types_property_active",
            "organization_id",
            "property_id",
            "is_active",
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

    code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    total_rooms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    max_adults: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    max_children: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    nightly_rate: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
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


class RoomTypeWrite(BaseModel):
    code: str = Field(
        min_length=1,
        max_length=64,
    )

    name: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = Field(
        default=None,
        max_length=1000,
    )

    total_rooms: int = Field(
        ge=1,
    )

    max_adults: int = Field(
        ge=1,
    )

    max_children: int = Field(
        default=0,
        ge=0,
    )

    nightly_rate: Decimal = Field(
        ge=0,
        max_digits=12,
        decimal_places=2,
    )

    currency: str = Field(
        min_length=3,
        max_length=3,
    )

    is_active: bool = True

    @field_validator(
        "code",
        "name",
    )
    @classmethod
    def normalize_required_text(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "Value cannot be blank."
            )

        return value

    @field_validator("currency")
    @classmethod
    def normalize_currency(
        cls,
        value: str,
    ) -> str:
        return value.strip().upper()


class RoomTypeResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID

    code: str
    name: str
    description: str | None

    total_rooms: int
    max_adults: int
    max_children: int

    nightly_rate: Decimal
    currency: str

    is_active: bool


def require_managed_property(
    tenant_context: TenantContext,
) -> UUID:
    """Require a selected property that the current user may manage."""

    property_id = tenant_context.property_id

    if property_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "A property must be selected "
                "using the X-Property-ID header."
            ),
        )

    try:
        require_property_management_access(
            tenant_context,
        )

    except TenantAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Property management access is required.",
        ) from exc

    return property_id


router = APIRouter(
    prefix="/admin/room-types",
    tags=["Room Inventory"],
)


@router.get(
    "",
    response_model=list[RoomTypeResponse],
)
async def list_room_types(
    tenant_context: TenantContextDependency,
    session: DatabaseSessionDependency,
) -> list[RoomTypeResponse]:
    """List room types for the selected property."""

    property_id = require_managed_property(
        tenant_context,
    )

    room_types = (
        await session.scalars(
            select(RoomType)
            .where(
                RoomType.organization_id
                == tenant_context.organization_id,
                RoomType.property_id
                == property_id,
            )
            .order_by(RoomType.name)
        )
    ).all()

    return [
        RoomTypeResponse.model_validate(room_type)
        for room_type in room_types
    ]


@router.post(
    "",
    response_model=RoomTypeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_room_type(
    payload: RoomTypeWrite,
    tenant_context: TenantContextDependency,
    session: DatabaseSessionDependency,
) -> RoomTypeResponse:
    """Create one room type."""

    property_id = require_managed_property(
        tenant_context,
    )

    room_type = RoomType(
        organization_id=tenant_context.organization_id,
        property_id=property_id,
        code=payload.code.upper(),
        name=payload.name,
        description=(
            payload.description.strip()
            if payload.description
            else None
        ),
        total_rooms=payload.total_rooms,
        max_adults=payload.max_adults,
        max_children=payload.max_children,
        nightly_rate=payload.nightly_rate,
        currency=payload.currency,
        is_active=payload.is_active,
    )

    session.add(room_type)

    await session.commit()
    await session.refresh(room_type)

    return RoomTypeResponse.model_validate(
        room_type,
    )


@router.put(
    "/{room_type_id}",
    response_model=RoomTypeResponse,
)
async def update_room_type(
    room_type_id: UUID,
    payload: RoomTypeWrite,
    tenant_context: TenantContextDependency,
    session: DatabaseSessionDependency,
) -> RoomTypeResponse:
    """Replace one room-type configuration."""

    property_id = require_managed_property(
        tenant_context,
    )

    room_type = await session.scalar(
        select(RoomType)
        .where(
            RoomType.id == room_type_id,
            RoomType.organization_id
            == tenant_context.organization_id,
            RoomType.property_id
            == property_id,
        )
        .with_for_update()
    )

    if room_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room type not found.",
        )

    room_type.code = payload.code.upper()
    room_type.name = payload.name
    room_type.description = (
        payload.description.strip()
        if payload.description
        else None
    )

    room_type.total_rooms = payload.total_rooms
    room_type.max_adults = payload.max_adults
    room_type.max_children = payload.max_children

    room_type.nightly_rate = payload.nightly_rate
    room_type.currency = payload.currency

    room_type.is_active = payload.is_active

    await session.commit()

    return RoomTypeResponse.model_validate(
        room_type,
    )