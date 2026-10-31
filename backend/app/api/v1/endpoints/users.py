from fastapi import APIRouter, Depends, Query

from app.api.deps import DEMO_USERS, get_current_user
from app.schemas.user import UserOut

router = APIRouter(tags=["Identity"])


@router.get("/users", response_model=list[UserOut])
async def list_users(
    include_simulated: bool = Query(default=False, description="Include simulated demo students"),
) -> list[UserOut]:
    """List available demo identities for the role switcher."""
    users = list(DEMO_USERS.values())
    if not include_simulated:
        users = [u for u in users if not u.is_simulated]
    return users


@router.get("/me", response_model=UserOut)
async def get_me(
    current_user: UserOut = Depends(get_current_user),
) -> UserOut:
    """Return the currently authenticated identity."""
    return current_user
