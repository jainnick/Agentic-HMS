from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
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
from sqlalchemy import (
    Enum as SqlEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.api.dependencies import (
    DatabaseSessionDependency,
    TenantContextDependency,
)
from app.db.base import Base
from app.modules.property_tools import (
    PropertyToolName,
    is_property_tool_enabled,
)
from app.modules.tenancy.context import TenantContext
from app.modules.tenancy.service import (
    TenantAccessDeniedError,
    require_property_management_access,
)

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RoomBookingStatus(StrEnum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Database models
# ---------------------------------------------------------------------------


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


class RoomBooking(Base):
    """
    One reservation against a room type.

    We reserve a quantity of a room type rather than assigning physical
    room numbers such as 101/102. Physical room assignment can be added later.
    """

    __tablename__ = "room_bookings"

    __table_args__ = (
        ForeignKeyConstraint(
            [
                "organization_id",
                "property_id",
                "room_type_id",
            ],
            [
                "room_types.organization_id",
                "room_types.property_id",
                "room_types.id",
            ],
            name="fk_room_bookings_room_type_tenant",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "confirmation_code",
            name="uq_room_bookings_confirmation_code",
        ),
        CheckConstraint(
            "check_out > check_in",
            name="ck_room_bookings_valid_stay",
        ),
        CheckConstraint(
            "rooms > 0",
            name="ck_room_bookings_rooms_positive",
        ),
        CheckConstraint(
            "adults > 0",
            name="ck_room_bookings_adults_positive",
        ),
        CheckConstraint(
            "children >= 0",
            name="ck_room_bookings_children_non_negative",
        ),
        CheckConstraint(
            "nightly_rate >= 0",
            name="ck_room_bookings_nightly_rate_non_negative",
        ),
        CheckConstraint(
            "total_amount >= 0",
            name="ck_room_bookings_total_amount_non_negative",
        ),
        CheckConstraint(
            "char_length(currency) = 3 AND currency = upper(currency)",
            name="ck_room_bookings_currency_code",
        ),
        Index(
            "ix_room_bookings_availability",
            "organization_id",
            "property_id",
            "room_type_id",
            "status",
            "check_in",
            "check_out",
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

    room_type_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )

    confirmation_code: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    guest_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    guest_email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
    )

    guest_phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    check_in: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    check_out: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    rooms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    adults: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    children: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    # Price snapshot.
    # If the hotel's current rate changes tomorrow, this booking retains
    # the price at which the guest booked.
    nightly_rate: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    status: Mapped[RoomBookingStatus] = mapped_column(
        SqlEnum(
            RoomBookingStatus,
            name="room_booking_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
        default=RoomBookingStatus.CONFIRMED,
        server_default=RoomBookingStatus.CONFIRMED.value,
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
# Room inventory API schemas
# ---------------------------------------------------------------------------


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
            raise ValueError("Value cannot be blank.")

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


# ---------------------------------------------------------------------------
# Availability / booking schemas
# ---------------------------------------------------------------------------


class RoomAvailabilityRequest(BaseModel):
    check_in: date
    check_out: date

    adults: int = Field(
        ge=1,
        le=20,
    )

    children: int = Field(
        default=0,
        ge=0,
        le=20,
    )

    rooms: int = Field(
        default=1,
        ge=1,
        le=10,
    )


class RoomAvailabilityOption(BaseModel):
    room_type_id: UUID

    code: str
    name: str

    available_rooms: int

    nightly_rate: Decimal
    currency: str


class RoomAvailabilityResponse(BaseModel):
    check_in: date
    check_out: date

    nights: int
    requested_rooms: int

    options: list[RoomAvailabilityOption]


class RoomBookingRequest(RoomAvailabilityRequest):
    room_type_id: UUID

    guest_name: str = Field(
        min_length=1,
        max_length=255,
    )

    guest_email: str | None = Field(
        default=None,
        max_length=320,
    )

    guest_phone: str | None = Field(
        default=None,
        max_length=50,
    )

    @field_validator("guest_name")
    @classmethod
    def normalize_guest_name(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Guest name cannot be blank.")

        return value


class RoomBookingResponse(BaseModel):
    confirmation_code: str

    room_type_id: UUID
    room_type_name: str

    check_in: date
    check_out: date

    rooms: int
    adults: int
    children: int

    nightly_rate: Decimal
    total_amount: Decimal
    currency: str

    status: RoomBookingStatus


# ---------------------------------------------------------------------------
# Domain errors
# ---------------------------------------------------------------------------


class RoomError(Exception):
    """Base room-domain error."""


class RoomValidationError(RoomError):
    """Raised when a room request is invalid."""


class RoomUnavailableError(RoomError):
    """Raised when requested inventory cannot be booked."""


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def require_managed_property(
    tenant_context: TenantContext,
) -> UUID:
    """Require a selected property that the current user may manage."""

    property_id = tenant_context.property_id

    if property_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=("A property must be selected using the X-Property-ID header."),
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


async def require_room_tool_enabled(
    session: AsyncSession,
    *,
    property_id: UUID,
    tool_name: PropertyToolName,
) -> None:
    """
    Enforce the effective PR4 capability setting for this property.
    """

    enabled = await is_property_tool_enabled(
        session,
        property_id=property_id,
        tool_name=tool_name,
    )

    if not enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(f"{tool_name.value} is disabled for this property."),
        )


def validate_stay(
    request: RoomAvailabilityRequest,
) -> int:
    """Validate dates and return the number of nights."""

    if request.check_out <= request.check_in:
        raise RoomValidationError("Check-out must be after check-in.")

    return (request.check_out - request.check_in).days


def room_supports_guests(
    room_type: RoomType,
    request: RoomAvailabilityRequest,
) -> bool:
    """
    Check simple MVP occupancy.

    Example:
    2 adults per room * 2 requested rooms = capacity for 4 adults.
    """

    return (
        request.adults <= room_type.max_adults * request.rooms
        and request.children <= room_type.max_children * request.rooms
    )


# ---------------------------------------------------------------------------
# Availability service
# ---------------------------------------------------------------------------


async def search_room_availability(
    session: AsyncSession,
    *,
    organization_id: UUID,
    property_id: UUID,
    request: RoomAvailabilityRequest,
) -> RoomAvailabilityResponse:
    """
    Calculate current availability.

    We do NOT store available_rooms in the database.

    available =
        room_type.total_rooms
        - overlapping confirmed booking quantities
    """

    nights = validate_stay(
        request,
    )

    # Calculate occupied inventory per room type.
    booked_inventory = (
        select(
            RoomBooking.room_type_id.label("room_type_id"),
            func.sum(RoomBooking.rooms).label("booked_rooms"),
        )
        .where(
            RoomBooking.organization_id == organization_id,
            RoomBooking.property_id == property_id,
            RoomBooking.status == RoomBookingStatus.CONFIRMED,
            # Two stays overlap when:
            #
            # existing check-in < requested checkout
            # existing checkout > requested check-in
            RoomBooking.check_in < request.check_out,
            RoomBooking.check_out > request.check_in,
        )
        .group_by(
            RoomBooking.room_type_id,
        )
        .subquery()
    )

    statement = (
        select(
            RoomType,
            func.coalesce(
                booked_inventory.c.booked_rooms,
                0,
            ).label("booked_rooms"),
        )
        .outerjoin(
            booked_inventory,
            booked_inventory.c.room_type_id == RoomType.id,
        )
        .where(
            RoomType.organization_id == organization_id,
            RoomType.property_id == property_id,
            RoomType.is_active.is_(True),
        )
        .order_by(
            RoomType.nightly_rate,
            RoomType.name,
        )
    )

    rows = (
        await session.execute(
            statement,
        )
    ).all()

    options: list[RoomAvailabilityOption] = []

    for room_type, booked_rooms in rows:
        if not room_supports_guests(
            room_type,
            request,
        ):
            continue

        available_rooms = max(
            room_type.total_rooms - int(booked_rooms),
            0,
        )

        if available_rooms < request.rooms:
            continue

        options.append(
            RoomAvailabilityOption(
                room_type_id=room_type.id,
                code=room_type.code,
                name=room_type.name,
                available_rooms=available_rooms,
                nightly_rate=room_type.nightly_rate,
                currency=room_type.currency,
            )
        )

    return RoomAvailabilityResponse(
        check_in=request.check_in,
        check_out=request.check_out,
        nights=nights,
        requested_rooms=request.rooms,
        options=options,
    )


# ---------------------------------------------------------------------------
# Booking service
# ---------------------------------------------------------------------------


async def create_room_booking(
    session: AsyncSession,
    *,
    organization_id: UUID,
    property_id: UUID,
    request: RoomBookingRequest,
) -> RoomBookingResponse:
    """
    Create a booking safely under concurrent requests.

    The critical sequence is:

        SELECT RoomType FOR UPDATE
        -> re-read current overlapping bookings
        -> verify inventory
        -> INSERT booking
        -> COMMIT

    The room-type row lock is held until COMMIT/ROLLBACK.
    """

    nights = validate_stay(
        request,
    )

    # This is the concurrency-control point.
    #
    # Two transactions trying to book this SAME room type cannot both
    # proceed through the critical availability check at the same time.
    room_type = await session.scalar(
        select(RoomType)
        .where(
            RoomType.id == request.room_type_id,
            RoomType.organization_id == organization_id,
            RoomType.property_id == property_id,
            RoomType.is_active.is_(True),
        )
        .with_for_update()
    )

    if room_type is None:
        await session.rollback()

        raise RoomUnavailableError("The requested room type is unavailable.")

    if not room_supports_guests(
        room_type,
        request,
    ):
        await session.rollback()

        raise RoomValidationError("The selected room type cannot accommodate the requested guests.")

    # This check MUST happen after FOR UPDATE.
    #
    # We intentionally do not trust an availability result that may have
    # been shown to the guest several seconds earlier.
    booked_rooms = await session.scalar(
        select(
            func.coalesce(
                func.sum(RoomBooking.rooms),
                0,
            )
        ).where(
            RoomBooking.organization_id == organization_id,
            RoomBooking.property_id == property_id,
            RoomBooking.room_type_id == room_type.id,
            RoomBooking.status == RoomBookingStatus.CONFIRMED,
            RoomBooking.check_in < request.check_out,
            RoomBooking.check_out > request.check_in,
        )
    )

    available_rooms = max(
        room_type.total_rooms - int(booked_rooms or 0),
        0,
    )

    if available_rooms < request.rooms:
        await session.rollback()

        raise RoomUnavailableError("The requested rooms are no longer available.")

    booking_id = uuid4()

    confirmation_code = f"HMS-{booking_id.hex[:12].upper()}"

    total_amount = room_type.nightly_rate * nights * request.rooms

    booking = RoomBooking(
        id=booking_id,
        organization_id=organization_id,
        property_id=property_id,
        room_type_id=room_type.id,
        confirmation_code=confirmation_code,
        guest_name=request.guest_name,
        guest_email=(request.guest_email.strip() if request.guest_email else None),
        guest_phone=(request.guest_phone.strip() if request.guest_phone else None),
        check_in=request.check_in,
        check_out=request.check_out,
        rooms=request.rooms,
        adults=request.adults,
        children=request.children,
        nightly_rate=room_type.nightly_rate,
        total_amount=total_amount,
        currency=room_type.currency,
        status=RoomBookingStatus.CONFIRMED,
    )

    session.add(
        booking,
    )

    await session.commit()

    return RoomBookingResponse(
        confirmation_code=confirmation_code,
        room_type_id=room_type.id,
        room_type_name=room_type.name,
        check_in=request.check_in,
        check_out=request.check_out,
        rooms=request.rooms,
        adults=request.adults,
        children=request.children,
        nightly_rate=room_type.nightly_rate,
        total_amount=total_amount,
        currency=room_type.currency,
        status=RoomBookingStatus.CONFIRMED,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


# We broaden the prefix from /admin/room-types to /admin so the SAME router
# can serve both room-type administration and reservation test endpoints.
#
# The existing external room-type URLs do not change.
router = APIRouter(
    prefix="/admin",
    tags=["Rooms"],
)


@router.get(
    "/room-types",
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
                RoomType.organization_id == tenant_context.organization_id,
                RoomType.property_id == property_id,
            )
            .order_by(
                RoomType.name,
            )
        )
    ).all()

    return [RoomTypeResponse.model_validate(room_type) for room_type in room_types]


@router.post(
    "/room-types",
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
        description=(payload.description.strip() if payload.description else None),
        total_rooms=payload.total_rooms,
        max_adults=payload.max_adults,
        max_children=payload.max_children,
        nightly_rate=payload.nightly_rate,
        currency=payload.currency,
        is_active=payload.is_active,
    )

    session.add(
        room_type,
    )

    await session.commit()
    await session.refresh(
        room_type,
    )

    return RoomTypeResponse.model_validate(
        room_type,
    )


@router.put(
    "/room-types/{room_type_id}",
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
            RoomType.organization_id == tenant_context.organization_id,
            RoomType.property_id == property_id,
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

    room_type.description = payload.description.strip() if payload.description else None

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


@router.post(
    "/rooms/availability-test",
    response_model=RoomAvailabilityResponse,
)
async def test_room_availability(
    payload: RoomAvailabilityRequest,
    tenant_context: TenantContextDependency,
    session: DatabaseSessionDependency,
) -> RoomAvailabilityResponse:
    """
    Test the reservation engine directly before exposing it to the LLM.
    """

    property_id = require_managed_property(
        tenant_context,
    )

    await require_room_tool_enabled(
        session,
        property_id=property_id,
        tool_name=(PropertyToolName.ROOM_AVAILABILITY),
    )

    try:
        return await search_room_availability(
            session,
            organization_id=(tenant_context.organization_id),
            property_id=property_id,
            request=payload,
        )

    except RoomValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post(
    "/rooms/bookings-test",
    response_model=RoomBookingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def test_room_booking(
    payload: RoomBookingRequest,
    tenant_context: TenantContextDependency,
    session: DatabaseSessionDependency,
) -> RoomBookingResponse:
    """
    Test transactional booking directly before exposing it to the LLM.
    """

    property_id = require_managed_property(
        tenant_context,
    )

    await require_room_tool_enabled(
        session,
        property_id=property_id,
        tool_name=(PropertyToolName.ROOM_BOOKING),
    )

    try:
        return await create_room_booking(
            session,
            organization_id=(tenant_context.organization_id),
            property_id=property_id,
            request=payload,
        )

    except RoomUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except RoomValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
