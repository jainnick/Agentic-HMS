from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CurrentUser(BaseModel):
    """Authenticated Supabase user available inside backend requests."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    email: str | None = None

    # This is the Supabase/Postgres auth role, normally "authenticated".
    # It is not the hotel role such as property_manager.
    auth_role: str
