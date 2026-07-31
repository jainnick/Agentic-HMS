from enum import StrEnum


class KnowledgeSourceType(StrEnum):
    """Supported sources for hotel knowledge documents."""

    PDF = "pdf"
    MANUAL = "manual"


class KnowledgeDocumentStatus(StrEnum):
    """Processing state of a hotel knowledge document."""

    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
