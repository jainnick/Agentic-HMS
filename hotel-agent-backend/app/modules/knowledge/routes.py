from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from app.api.dependencies import (
    DatabaseSessionDependency,
    TenantContextDependency,
)
from app.core.config import get_settings
from app.modules.knowledge.chunking import ChunkingError
from app.modules.knowledge.embeddings import EmbeddingError
from app.modules.knowledge.extraction import PdfExtractionError
from app.modules.knowledge.ingestion import (
    KnowledgeIngestionValidationError,
)
from app.modules.knowledge.repository import (
    KnowledgeRepositoryError,
)
from app.modules.knowledge.schemas import (
    KnowledgePdfUploadResponse,
)
from app.modules.knowledge.service import (
    DuplicateKnowledgeDocumentError,
    KnowledgeDocumentCreationConflictError,
    ingest_pdf_document,
)
from app.modules.tenancy.service import (
    TenantAccessDeniedError,
    require_property_management_access,
)


router = APIRouter(
    prefix="/admin/knowledge/documents",
    tags=["Knowledge Admin"],
)


async def read_limited_upload(
    file: UploadFile,
    *,
    max_upload_mb: int,
) -> bytes:
    """
    Read at most the configured upload size plus one byte.

    Reading only max_bytes + 1 prevents a client from making the application
    load an arbitrarily large file into memory before validation occurs.
    """

    max_upload_bytes = max_upload_mb * 1024 * 1024

    file_bytes = await file.read(max_upload_bytes + 1)

    if len(file_bytes) > max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(f"Uploaded PDF exceeds the {max_upload_mb} MB size limit."),
        )

    return file_bytes


@router.post(
    "/pdf",
    response_model=KnowledgePdfUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_pdf_knowledge_document(
    title: Annotated[
        str,
        Form(
            description=("Human-readable document title, such as Guest Policies."),
        ),
    ],
    source_key: Annotated[
        str,
        Form(
            description=("Stable identifier shared by versions of the same source."),
        ),
    ],
    file: Annotated[
        UploadFile,
        File(
            description="PDF containing hotel knowledge.",
        ),
    ],
    tenant_context: TenantContextDependency,
    session: DatabaseSessionDependency,
) -> KnowledgePdfUploadResponse:
    """
    Upload and fully process one hotel knowledge PDF.

    Only organization owners, property managers, and operations managers may
    manage knowledge documents for the selected property.
    """

    property_id = tenant_context.property_id

    if property_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=("A property must be selected using the X-Property-ID header."),
        )

    try:
        require_property_management_access(tenant_context)

    except TenantAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    settings = get_settings()

    try:
        pdf_bytes = await read_limited_upload(
            file,
            max_upload_mb=(settings.knowledge_max_upload_mb),
        )

    finally:
        await file.close()

    try:
        result = await ingest_pdf_document(
            session,
            organization_id=(tenant_context.organization_id),
            property_id=property_id,
            created_by=tenant_context.user_id,
            title=title,
            source_key=source_key,
            filename=file.filename,
            content_type=file.content_type,
            pdf_bytes=pdf_bytes,
        )

    except KnowledgeIngestionValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except DuplicateKnowledgeDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(exc),
                "existing_document_id": str(exc.existing_document_id),
                "existing_version_number": (exc.existing_version_number),
            },
        ) from exc

    except KnowledgeDocumentCreationConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except (
        PdfExtractionError,
        ChunkingError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    except EmbeddingError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=("The embedding service could not process the uploaded document."),
        ) from exc

    except KnowledgeRepositoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=("The document could not be stored."),
        ) from exc

    document = result.document

    return KnowledgePdfUploadResponse(
        id=document.id,
        organization_id=document.organization_id,
        property_id=document.property_id,
        title=document.title,
        source_type=document.source_type,
        original_filename=document.original_filename,
        source_key=document.source_key,
        version_number=document.version_number,
        status=document.status,
        is_active=document.is_active,
        chunk_count=result.chunk_count,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )
