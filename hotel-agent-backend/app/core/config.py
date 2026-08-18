from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "Agentic Hotel Management API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str
    database_pool_size: int = 5
    database_max_overflow: int = 5
    database_timeout_seconds: int = 10
    database_ssl_mode: str = "require"
    sql_echo: bool = False

    # Supabase project configuration.
    supabase_url: str | None = None
    supabase_anon_key: SecretStr | None = None
    supabase_service_role_key: SecretStr | None = None

    # Supabase user access tokens normally use "authenticated".
    supabase_jwt_audience: str = "authenticated"

    # These can be derived from SUPABASE_URL, but may be overridden.
    supabase_jwt_issuer: str | None = None
    supabase_jwks_url: str | None = None

    # Small allowance for clock differences between systems.
    supabase_jwt_leeway_seconds: int = 30

    # Knowledge embeddings
    #
    # This model produces 384-dimensional vectors. The value must remain
    # aligned with knowledge_chunks.embedding VECTOR(384).
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    embedding_batch_size: int = 32

    # PDF ingestion
    knowledge_max_upload_mb: int = 10

    # Adaptive PDF chunking.
    #
    # target_tokens:
    #     preferred chunk size when a natural PDF block boundary exists.
    #
    # max_tokens:
    #     hard upper limit before sentence/token splitting is required.
    #
    # fallback_overlap_tokens:
    #     overlap used only for forced tokenizer-window splitting.
    knowledge_chunk_target_tokens: int = 160
    knowledge_chunk_max_tokens: int = 220
    knowledge_chunk_fallback_overlap_tokens: int = 20

    # Retrieval defaults
    rag_match_count: int = 6
    rag_min_similarity: float = 0.45

    # Primary LLM - Groq
    llm_api_key: SecretStr | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None

    # Fallback LLM - NVIDIA NIM
    nvidia_api_key: SecretStr | None = None
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "mistralai/mistral-nemotron"

    # Assistant runtime
    llm_timeout_seconds: float = 30.0
    llm_max_output_tokens: int = 600

    assistant_max_message_length: int = 4_000
    assistant_max_tool_rounds: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_knowledge_configuration(self) -> Settings:
        """
        Reject settings that would make ingestion unreliable.

        The database currently stores VECTOR(384), so a different embedding
        dimension would cause inserts to fail.
        """

        if self.embedding_dimension != 384:
            raise ValueError(
                "EMBEDDING_DIMENSION must remain 384 because "
                "knowledge_chunks.embedding uses VECTOR(384)."
            )

        if self.embedding_batch_size <= 0:
            raise ValueError("EMBEDDING_BATCH_SIZE must be greater than zero.")

        if self.knowledge_max_upload_mb <= 0:
            raise ValueError("KNOWLEDGE_MAX_UPLOAD_MB must be greater than zero.")

        if self.knowledge_chunk_target_tokens <= 0:
            raise ValueError("KNOWLEDGE_CHUNK_TARGET_TOKENS must be greater than zero.")

        if self.knowledge_chunk_max_tokens <= 0:
            raise ValueError("KNOWLEDGE_CHUNK_MAX_TOKENS must be greater than zero.")

        if self.knowledge_chunk_target_tokens > self.knowledge_chunk_max_tokens:
            raise ValueError(
                "KNOWLEDGE_CHUNK_TARGET_TOKENS cannot be greater than KNOWLEDGE_CHUNK_MAX_TOKENS."
            )

        if self.knowledge_chunk_fallback_overlap_tokens < 0:
            raise ValueError("KNOWLEDGE_CHUNK_FALLBACK_OVERLAP_TOKENS cannot be negative.")

        if self.knowledge_chunk_fallback_overlap_tokens >= self.knowledge_chunk_max_tokens:
            raise ValueError(
                "KNOWLEDGE_CHUNK_FALLBACK_OVERLAP_TOKENS must be smaller "
                "than KNOWLEDGE_CHUNK_MAX_TOKENS."
            )

        if self.rag_match_count <= 0:
            raise ValueError("RAG_MATCH_COUNT must be greater than zero.")

        if not 0 <= self.rag_min_similarity <= 1:
            raise ValueError("RAG_MIN_SIMILARITY must be between 0 and 1.")

        if self.llm_timeout_seconds <= 0:
            raise ValueError("LLM_TIMEOUT_SECONDS must be greater than zero.")

        if self.llm_max_output_tokens <= 0:
            raise ValueError("LLM_MAX_OUTPUT_TOKENS must be greater than zero.")

        if self.assistant_max_message_length <= 0:
            raise ValueError("ASSISTANT_MAX_MESSAGE_LENGTH must be greater than zero.")

        if not 1 <= self.assistant_max_tool_rounds <= 10:
            raise ValueError("ASSISTANT_MAX_TOOL_ROUNDS must be between 1 and 10.")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
