from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)
from sqlalchemy import (
    func,
    or_,
    select,
)

from app.modules.assistant.context import (
    AssistantToolContext,
)
from app.modules.assistant.sessions import (
    AssistantSession,
    PendingRoomBooking,
    clear_pending_booking,
    get_pending_booking,
    set_pending_booking,
)
from app.modules.rooms import (
    RoomAvailabilityRequest,
    RoomAvailabilityResponse,
    RoomBookingRequest,
    RoomType,
    RoomUnavailableError,
    create_room_booking,
    search_room_availability,
    validate_stay,
)

ROOM_AVAILABILITY_TOOL_NAME = "room_availability"

ROOM_AVAILABILITY_TOOL_LABEL = "room.availability"

ROOM_BOOKING_TOOL_NAME = "room_booking"

ROOM_BOOKING_TOOL_LABEL = "room.booking"


# ---------------------------------------------------------------------------
# Availability tool
# ---------------------------------------------------------------------------


class RoomAvailabilityToolInput(RoomAvailabilityRequest):
    """
    Arguments the LLM may provide for live availability.

    organization_id and property_id are intentionally excluded.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    adults: int = Field(
        default=1,
        ge=1,
        le=20,
        description=("Number of adults staying."),
    )

    room_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description=(
            "Optional room type wording supplied "
            "by the guest. It may be a full room "
            "name, room code, or partial room "
            "name such as 'Deluxe'."
        ),
        examples=[
            "Deluxe King",
            "Deluxe",
            "DLX-KING",
        ],
    )


class RoomAvailabilityToolResult(RoomAvailabilityResponse):
    """
    Operational availability result sent to the LLM.
    """

    requested_room_type: str | None = None

    room_type_found: bool = True

    room_type_ambiguous: bool = False

    matching_room_types: list[str] = Field(
        default_factory=list,
    )


async def find_room_type_matches(
    *,
    context: AssistantToolContext,
    room_type: str,
) -> list[RoomType]:
    """
    Resolve guest room wording deterministically.

    Order:
    1. exact name/code match
    2. partial room-name match
    """

    normalized = room_type.strip().lower()

    exact_statement = (
        select(RoomType)
        .where(
            RoomType.organization_id == context.organization_id,
            RoomType.property_id == context.property_id,
            RoomType.is_active.is_(True),
            or_(
                func.lower(RoomType.name) == normalized,
                func.lower(RoomType.code) == normalized,
            ),
        )
        .order_by(RoomType.name)
    )

    exact_matches = list((await context.session.scalars(exact_statement)).all())

    if exact_matches:
        return exact_matches

    partial_statement = (
        select(RoomType)
        .where(
            RoomType.organization_id == context.organization_id,
            RoomType.property_id == context.property_id,
            RoomType.is_active.is_(True),
            func.lower(RoomType.name).like(f"%{normalized}%"),
        )
        .order_by(RoomType.name)
    )

    return list((await context.session.scalars(partial_statement)).all())


async def execute_room_availability_tool(
    tool_input: RoomAvailabilityToolInput,
    *,
    context: AssistantToolContext,
) -> RoomAvailabilityToolResult:
    """
    Thin AI adapter over the existing PR6 availability service.
    """

    request = RoomAvailabilityRequest.model_validate(
        tool_input.model_dump(
            exclude={
                "room_type",
            }
        )
    )

    if tool_input.room_type is None:
        availability = await search_room_availability(
            context.session,
            organization_id=(context.organization_id),
            property_id=(context.property_id),
            request=request,
        )

        return RoomAvailabilityToolResult(
            check_in=(availability.check_in),
            check_out=(availability.check_out),
            nights=availability.nights,
            requested_rooms=(availability.requested_rooms),
            options=availability.options,
        )

    matches = await find_room_type_matches(
        context=context,
        room_type=(tool_input.room_type),
    )

    if not matches:
        nights = validate_stay(request)

        return RoomAvailabilityToolResult(
            check_in=request.check_in,
            check_out=request.check_out,
            nights=nights,
            requested_rooms=(request.rooms),
            options=[],
            requested_room_type=(tool_input.room_type),
            room_type_found=False,
        )

    if len(matches) > 1:
        nights = validate_stay(request)

        return RoomAvailabilityToolResult(
            check_in=request.check_in,
            check_out=request.check_out,
            nights=nights,
            requested_rooms=(request.rooms),
            options=[],
            requested_room_type=(tool_input.room_type),
            room_type_found=True,
            room_type_ambiguous=True,
            matching_room_types=[match.name for match in matches],
        )

    target_room_type = matches[0]

    availability = await search_room_availability(
        context.session,
        organization_id=(context.organization_id),
        property_id=(context.property_id),
        request=request,
        room_type_id=(target_room_type.id),
    )

    return RoomAvailabilityToolResult(
        check_in=availability.check_in,
        check_out=availability.check_out,
        nights=availability.nights,
        requested_rooms=(availability.requested_rooms),
        options=availability.options,
        requested_room_type=(tool_input.room_type),
        room_type_found=True,
        room_type_ambiguous=False,
        matching_room_types=[target_room_type.name],
    )


# ---------------------------------------------------------------------------
# Booking tool
# ---------------------------------------------------------------------------


class RoomBookingToolInput(BaseModel):
    """
    LLM-facing booking command.

    confirm=False:
        Prepare/quote a booking.

    confirm=True:
        Confirm the booking already stored in the
        server-side assistant session.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    confirm: bool = Field(
        default=False,
        description=(
            "Set true only after the guest explicitly confirms the previously quoted booking."
        ),
    )

    room_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    check_in: date | None = None

    check_out: date | None = None

    adults: int | None = Field(
        default=None,
        ge=1,
        le=20,
    )

    children: int | None = Field(
        default=None,
        ge=0,
        le=20,
    )

    rooms: int = Field(
        default=1,
        ge=1,
        le=10,
    )

    guest_name: str | None = Field(
        default=None,
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


class RoomBookingToolResult(BaseModel):
    """
    Structured booking workflow response for the LLM.
    """

    status: Literal[
        "missing_information",
        "room_not_found",
        "room_ambiguous",
        "unavailable",
        "confirmation_required",
        "confirmation_not_explicit",
        "confirmed",
    ]

    missing_fields: list[str] = Field(
        default_factory=list,
    )

    matching_room_types: list[str] = Field(
        default_factory=list,
    )

    room_type_name: str | None = None

    check_in: date | None = None
    check_out: date | None = None

    adults: int | None = None
    children: int | None = None
    rooms: int | None = None

    nightly_rate: Decimal | None = None

    total_amount: Decimal | None = None

    currency: str | None = None

    confirmation_code: str | None = None


def is_explicit_booking_confirmation(
    message: str,
) -> bool:
    """
    Conservatively validate final booking confirmation.

    We check the user's actual text in addition to the
    LLM's confirm=true argument.

    False negatives are safer than false positives for
    a write operation.
    """

    normalized = " ".join(message.lower().strip().split())

    normalized = re.sub(
        r"[.!?,]+$",
        "",
        normalized,
    )

    explicit_phrases = {
        "yes",
        "yes please",
        "yes book it",
        "yes please book it",
        "yes confirm",
        "yes confirm it",
        "confirm",
        "confirm it",
        "confirm booking",
        "confirm the booking",
        "book it",
        "please book it",
        "go ahead",
        "yes go ahead",
        "proceed",
        "yes proceed",
    }

    return normalized in explicit_phrases


async def prepare_room_booking(
    tool_input: RoomBookingToolInput,
    *,
    context: AssistantToolContext,
    assistant_session: AssistantSession,
) -> RoomBookingToolResult:
    """
    Validate and quote a booking.

    NO RoomBooking database row is created here.
    """

    required_values = {
        "room_type": (tool_input.room_type),
        "check_in": (tool_input.check_in),
        "check_out": (tool_input.check_out),
        "adults": (tool_input.adults),
        "children": (tool_input.children),
        "guest_name": (tool_input.guest_name),
    }

    missing_fields = [name for name, value in required_values.items() if value is None]

    if missing_fields:
        return RoomBookingToolResult(
            status="missing_information",
            missing_fields=(missing_fields),
        )

    # These are guaranteed by the checks above.
    assert tool_input.room_type is not None
    assert tool_input.check_in is not None
    assert tool_input.check_out is not None
    assert tool_input.adults is not None
    assert tool_input.children is not None
    assert tool_input.guest_name is not None

    matches = await find_room_type_matches(
        context=context,
        room_type=(tool_input.room_type),
    )

    if not matches:
        return RoomBookingToolResult(
            status="room_not_found",
        )

    if len(matches) > 1:
        return RoomBookingToolResult(
            status="room_ambiguous",
            matching_room_types=[room_type.name for room_type in matches],
        )

    room_type = matches[0]

    availability_request = RoomAvailabilityRequest(
        check_in=(tool_input.check_in),
        check_out=(tool_input.check_out),
        adults=(tool_input.adults),
        children=(tool_input.children),
        rooms=tool_input.rooms,
    )

    availability = await search_room_availability(
        context.session,
        organization_id=(context.organization_id),
        property_id=(context.property_id),
        request=(availability_request),
        room_type_id=(room_type.id),
    )

    if not availability.options:
        return RoomBookingToolResult(
            status="unavailable",
            room_type_name=(room_type.name),
            check_in=(tool_input.check_in),
            check_out=(tool_input.check_out),
        )

    option = availability.options[0]

    total_amount = option.nightly_rate * availability.nights * tool_input.rooms

    pending_booking = PendingRoomBooking(
        idempotency_key=uuid4(),
        room_type_id=(room_type.id),
        room_type_name=(room_type.name),
        check_in=(tool_input.check_in),
        check_out=(tool_input.check_out),
        adults=(tool_input.adults),
        children=(tool_input.children),
        rooms=tool_input.rooms,
        guest_name=(tool_input.guest_name),
        guest_email=(tool_input.guest_email),
        guest_phone=(tool_input.guest_phone),
        nightly_rate=(option.nightly_rate),
        total_amount=(total_amount),
        currency=(option.currency),
    )

    await set_pending_booking(
        context.session,
        assistant_session=(assistant_session),
        pending_booking=(pending_booking),
    )

    return RoomBookingToolResult(
        status="confirmation_required",
        room_type_name=(room_type.name),
        check_in=(tool_input.check_in),
        check_out=(tool_input.check_out),
        adults=tool_input.adults,
        children=tool_input.children,
        rooms=tool_input.rooms,
        nightly_rate=(option.nightly_rate),
        total_amount=total_amount,
        currency=option.currency,
    )


async def confirm_pending_room_booking(
    *,
    context: AssistantToolContext,
    assistant_session: AssistantSession,
    user_message: str,
) -> RoomBookingToolResult:
    """
    Confirm the server-stored booking after explicit user consent.

    Importantly, booking details are NOT regenerated
    by the LLM at this stage.
    """

    pending = get_pending_booking(assistant_session)

    if pending is None:
        return RoomBookingToolResult(
            status="missing_information",
            missing_fields=["pending_booking"],
        )

    if not is_explicit_booking_confirmation(user_message):
        return RoomBookingToolResult(
            status=("confirmation_not_explicit"),
            room_type_name=(pending.room_type_name),
            check_in=pending.check_in,
            check_out=pending.check_out,
            adults=pending.adults,
            children=pending.children,
            rooms=pending.rooms,
            nightly_rate=(pending.nightly_rate),
            total_amount=(pending.total_amount),
            currency=pending.currency,
        )

    booking_request = RoomBookingRequest(
        room_type_id=(pending.room_type_id),
        check_in=pending.check_in,
        check_out=pending.check_out,
        adults=pending.adults,
        children=pending.children,
        rooms=pending.rooms,
        guest_name=(pending.guest_name),
        guest_email=(pending.guest_email),
        guest_phone=(pending.guest_phone),
    )

    try:
        booking = await create_room_booking(
            context.session,
            organization_id=(context.organization_id),
            property_id=(context.property_id),
            request=booking_request,
            idempotency_key=(pending.idempotency_key),
        )

    except RoomUnavailableError:
        await clear_pending_booking(
            context.session,
            assistant_session=(assistant_session),
        )

        return RoomBookingToolResult(
            status="unavailable",
            room_type_name=(pending.room_type_name),
            check_in=(pending.check_in),
            check_out=(pending.check_out),
        )

    await clear_pending_booking(
        context.session,
        assistant_session=(assistant_session),
    )

    return RoomBookingToolResult(
        status="confirmed",
        room_type_name=(booking.room_type_name),
        check_in=booking.check_in,
        check_out=booking.check_out,
        adults=booking.adults,
        children=booking.children,
        rooms=booking.rooms,
        nightly_rate=(booking.nightly_rate),
        total_amount=(booking.total_amount),
        currency=booking.currency,
        confirmation_code=(booking.confirmation_code),
    )


async def execute_room_booking_tool(
    tool_input: RoomBookingToolInput,
    *,
    context: AssistantToolContext,
    assistant_session: AssistantSession,
    user_message: str,
) -> RoomBookingToolResult:
    """
    Single AI adapter entry point for booking.

    confirm=False
        -> prepare/quote

    confirm=True
        -> confirm stored booking
    """

    if tool_input.confirm:
        return await confirm_pending_room_booking(
            context=context,
            assistant_session=(assistant_session),
            user_message=(user_message),
        )

    return await prepare_room_booking(
        tool_input,
        context=context,
        assistant_session=(assistant_session),
    )
