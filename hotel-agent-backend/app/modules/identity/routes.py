from fastapi import APIRouter

from app.api.dependencies import CurrentUserDependency
from app.modules.identity.schemas import CurrentUser

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.get(
    "/me",
    response_model=CurrentUser,
)
async def get_authenticated_user(
    current_user: CurrentUserDependency,
) -> CurrentUser:
    """Return the authenticated Supabase user's identity."""

    return current_user
