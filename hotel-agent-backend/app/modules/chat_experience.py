from __future__ import annotations

import json
from typing import Annotated
from urllib.parse import quote
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select, text

from app.api.dependencies import DatabaseSessionDependency, TenantContextDependency
from app.core.config import get_settings
from app.modules.assistant.sessions import (
    AssistantSession,
    get_conversation_history,
    get_pending_booking,
)
from app.modules.portal import resolve_public_property
from app.modules.rooms import require_managed_property

router = APIRouter(tags=["Chat Experience"])

ROOM_IMAGE_BUCKET = "room-images"
ROOM_IMAGE_MAX_BYTES = 5 * 1024 * 1024
ROOM_IMAGE_MIME_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


class ChatHistoryMessage(BaseModel):
    role: str
    content: str


class ChatPendingBooking(BaseModel):
    room_type_name: str
    total_amount: str
    currency: str


class WidgetSessionResponse(BaseModel):
    session_id: UUID
    messages: list[ChatHistoryMessage]
    pending_booking: ChatPendingBooking | None = None


class RoomMediaResponse(BaseModel):
    room_type_id: UUID
    code: str
    name: str
    room_images: list[str] = Field(default_factory=list)


class RoomMediaListResponse(BaseModel):
    rooms: list[RoomMediaResponse] = Field(default_factory=list)


def _media_from_row(row: object) -> RoomMediaResponse:
    mapping = row._mapping  # type: ignore[attr-defined]
    images = mapping["room_images"]
    return RoomMediaResponse(
        room_type_id=mapping["id"],
        code=mapping["code"],
        name=mapping["name"],
        room_images=list(images) if isinstance(images, list) else [],
    )


async def _list_room_media(
    session: DatabaseSessionDependency,
    *,
    organization_id: UUID,
    property_id: UUID,
) -> RoomMediaListResponse:
    rows = (
        await session.execute(
            text(
                """
                SELECT id, code, name, room_images
                FROM public.room_types
                WHERE organization_id = :organization_id
                  AND property_id = :property_id
                ORDER BY nightly_rate, name
                """
            ),
            {
                "organization_id": organization_id,
                "property_id": property_id,
            },
        )
    ).all()
    return RoomMediaListResponse(rooms=[_media_from_row(row) for row in rows])


@router.get(
    "/widget/{property_code}/sessions/{session_id}",
    response_model=WidgetSessionResponse,
)
async def get_widget_session(
    property_code: str,
    session_id: UUID,
    session: DatabaseSessionDependency,
) -> WidgetSessionResponse:
    property_, _ = await resolve_public_property(session, property_code)
    assistant_session = await session.scalar(
        select(AssistantSession).where(
            AssistantSession.id == session_id,
            AssistantSession.organization_id == property_.organization_id,
            AssistantSession.property_id == property_.id,
        )
    )
    if assistant_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")

    pending = get_pending_booking(assistant_session)
    return WidgetSessionResponse(
        session_id=assistant_session.id,
        messages=[
            ChatHistoryMessage(role=item["role"], content=item["content"])
            for item in get_conversation_history(assistant_session)
        ],
        pending_booking=(
            ChatPendingBooking(
                room_type_name=pending.room_type_name,
                total_amount=str(pending.total_amount),
                currency=pending.currency,
            )
            if pending is not None
            else None
        ),
    )


@router.delete(
    "/widget/{property_code}/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_widget_session(
    property_code: str,
    session_id: UUID,
    session: DatabaseSessionDependency,
) -> Response:
    property_, _ = await resolve_public_property(session, property_code)
    assistant_session = await session.scalar(
        select(AssistantSession).where(
            AssistantSession.id == session_id,
            AssistantSession.organization_id == property_.organization_id,
            AssistantSession.property_id == property_.id,
        )
    )
    if assistant_session is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    await session.delete(assistant_session)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/widget/{property_code}/room-media",
    response_model=RoomMediaListResponse,
)
async def get_widget_room_media(
    property_code: str,
    session: DatabaseSessionDependency,
) -> RoomMediaListResponse:
    property_, _ = await resolve_public_property(session, property_code)
    return await _list_room_media(
        session,
        organization_id=property_.organization_id,
        property_id=property_.id,
    )


@router.get(
    "/admin/room-media",
    response_model=RoomMediaListResponse,
)
async def get_admin_room_media(
    tenant_context: TenantContextDependency,
    session: DatabaseSessionDependency,
) -> RoomMediaListResponse:
    property_id = require_managed_property(tenant_context)
    return await _list_room_media(
        session,
        organization_id=tenant_context.organization_id,
        property_id=property_id,
    )


@router.post(
    "/admin/room-types/{room_type_id}/images",
    response_model=RoomMediaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_room_image(
    room_type_id: UUID,
    file: Annotated[UploadFile, File(description="JPEG, PNG, or WebP room photo.")],
    tenant_context: TenantContextDependency,
    session: DatabaseSessionDependency,
) -> RoomMediaResponse:
    property_id = require_managed_property(tenant_context)
    row = (
        await session.execute(
            text(
                """
                SELECT id, code, name, room_images
                FROM public.room_types
                WHERE id = :room_type_id
                  AND organization_id = :organization_id
                  AND property_id = :property_id
                """
            ),
            {
                "room_type_id": room_type_id,
                "organization_id": tenant_context.organization_id,
                "property_id": property_id,
            },
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found.")

    current = _media_from_row(row)
    if len(current.room_images) >= 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A room type can have at most 8 photos.",
        )

    extension = ROOM_IMAGE_MIME_TYPES.get(file.content_type or "")
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Room photos must be JPEG, PNG, or WebP.",
        )

    try:
        image_bytes = await file.read(ROOM_IMAGE_MAX_BYTES + 1)
    finally:
        await file.close()

    if not image_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The image is empty.")
    if len(image_bytes) > ROOM_IMAGE_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Room photos must be 5 MB or smaller.",
        )

    settings = get_settings()
    if settings.supabase_url is None or settings.supabase_service_role_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Room photo storage is not configured.",
        )

    object_path = (
        f"{tenant_context.organization_id}/{property_id}/{room_type_id}/{uuid4().hex}.{extension}"
    )
    service_key = settings.supabase_service_role_key.get_secret_value()
    upload_url = (
        f"{settings.supabase_url.rstrip('/')}/storage/v1/object/"
        f"{ROOM_IMAGE_BUCKET}/{quote(object_path, safe='/')}"
    )

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            upload_url,
            content=image_bytes,
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
                "Content-Type": file.content_type or "application/octet-stream",
                "x-upsert": "false",
            },
        )
    if response.status_code >= 300:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Room photo upload could not be completed.",
        )

    public_url = (
        f"{settings.supabase_url.rstrip('/')}/storage/v1/object/public/"
        f"{ROOM_IMAGE_BUCKET}/{quote(object_path, safe='/')}"
    )
    updated_row = (
        await session.execute(
            text(
                """
                UPDATE public.room_types
                SET room_images = COALESCE(room_images, '[]'::jsonb)
                    || CAST(:new_images AS jsonb),
                    updated_at = now()
                WHERE id = :room_type_id
                  AND organization_id = :organization_id
                  AND property_id = :property_id
                RETURNING id, code, name, room_images
                """
            ),
            {
                "new_images": json.dumps([public_url]),
                "room_type_id": room_type_id,
                "organization_id": tenant_context.organization_id,
                "property_id": property_id,
            },
        )
    ).first()
    await session.commit()

    if updated_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found.")
    return _media_from_row(updated_row)
