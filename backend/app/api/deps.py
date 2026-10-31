from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, UnknownUserError
from app.db.session import get_db_session
from app.schemas.user import UserOut, UserRole

# Standard demo identities as defined in docs/database.md
DEMO_USERS = {
    1: UserOut(id=1, display_name="Aarav", role=UserRole.STUDENT, is_simulated=False, classroom_id=1),
    2: UserOut(id=2, display_name="Ms. Rao", role=UserRole.TEACHER, is_simulated=False, classroom_id=1),
}


async def get_current_user(
    x_demo_user_id: Annotated[int | None, Header(alias="X-Demo-User-Id")] = None,
    session: AsyncSession = Depends(get_db_session),
) -> UserOut:
    if x_demo_user_id is None:
        raise UnknownUserError("Missing X-Demo-User-Id header")

    # In M0/pre-seed or fallback:
    if x_demo_user_id in DEMO_USERS:
        return DEMO_USERS[x_demo_user_id]

    raise UnknownUserError(f"User id {x_demo_user_id} not found")


async def require_teacher(
    current_user: Annotated[UserOut, Depends(get_current_user)],
) -> UserOut:
    if current_user.role != UserRole.TEACHER:
        raise ForbiddenError("Only teachers can access this resource")
    return current_user
