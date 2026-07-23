from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "Agentic Hotel Management API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"

    database_url: str
    database_pool_size: int = 5
    database_max_overflow: int = 5
    database_timeout_seconds: int = 10
    database_ssl_mode: str = "require"

    sql_echo: bool = False

    # Supabase project configuration.
    #
    # These remain optional while authentication is being introduced so that
    # existing health checks and unit tests can still start without Supabase
    # Auth configuration. Protected routes will return 503 when they are absent.
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
