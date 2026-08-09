from __future__ import annotations

from pydantic import ConfigDict, Field
from sqlalchemy import func, or_, select

from app.modules.assistant.context import (
    AssistantToolContext,
)
from app.modules.rooms import (
    RoomAvailabilityRequest,
    RoomAvailabilityResponse,
    RoomType,
    search_room_availability,
    validate_stay,
)

ROOM_AVAILABILITY_TOOL_NAME = "room_availability"

ROOM_AVAILABILITY_TOOL_LABEL = "room.availability"


class RoomAvailabilityToolInput(RoomAvailabilityRequest):
    """
    Arguments the LLM is allowed to provide for
    live room availability.

    organization_id and property_id are deliberately
    absent. Those values come from trusted backend
    context rather than the language model.
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
            "by the guest. It may be a complete "
            "room name, room code, or partial room "
            "name such as 'Deluxe'. Leave empty "
            "when checking all room types."
        ),
        examples=[
            "Deluxe King",
            "Deluxe",
            "DLX-KING",
        ],
    )


class RoomAvailabilityToolResult(RoomAvailabilityResponse):
    """
    Structured operational result returned to the LLM.

    These additional fields let the model distinguish:
    - room not found
    - ambiguous room wording
    - room exists but is sold out
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

    Resolution order:

    1. exact case-insensitive name/code match
    2. partial case-insensitive name match

    We intentionally do not use embeddings or let the
    LLM guess structured database entities.
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
    Adapt an LLM-generated availability request to
    the already-tested PR6 room service.

    This function performs translation and entity
    resolution only.

    Availability calculations stay in rooms.py.
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
            check_in=availability.check_in,
            check_out=availability.check_out,
            nights=availability.nights,
            requested_rooms=(availability.requested_rooms),
            options=availability.options,
        )

    matches = await find_room_type_matches(
        context=context,
        room_type=tool_input.room_type,
    )

    if not matches:
        nights = validate_stay(request)

        return RoomAvailabilityToolResult(
            check_in=request.check_in,
            check_out=request.check_out,
            nights=nights,
            requested_rooms=request.rooms,
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
            requested_rooms=request.rooms,
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
        room_type_id=target_room_type.id,
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
