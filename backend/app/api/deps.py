from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ForbiddenError, UnknownUserError
from app.core.limits import user_rate_limiter
from app.db.session import get_db_session
from app.models.entities import User
from app.schemas.user import UserOut, UserRole

# Standard demo identities as defined in docs/database.md
DEMO_USERS = {
    1: UserOut(
        id=1, display_name="Aarav", role=UserRole.STUDENT, is_simulated=False, classroom_id=1
    ),
    2: UserOut(
        id=2, display_name="Ms. Rao", role=UserRole.TEACHER, is_simulated=False, classroom_id=1
    ),
}


async def get_current_user(
    x_demo_user_id: Annotated[int | None, Header(alias="X-Demo-User-Id")] = None,
    session: AsyncSession = Depends(get_db_session),
) -> UserOut:
    settings = get_settings()

    # Reject demo identity header in production unless explicitly enabled
    if settings.ENV == "production" and not settings.ALLOW_DEMO_AUTH:
        raise ForbiddenError("Demo authentication is disabled in production environment")

    if x_demo_user_id is None:
        raise UnknownUserError("Missing X-Demo-User-Id header")

    # In development / demo mode or test fixture:
    if x_demo_user_id in DEMO_USERS:
        return DEMO_USERS[x_demo_user_id]

    try:
        db_user = await session.get(User, x_demo_user_id)
        if db_user:
            return UserOut(
                id=db_user.id,
                display_name=db_user.display_name,
                role=UserRole(db_user.role.value),
                is_simulated=db_user.is_simulated,
                classroom_id=db_user.classroom_id,
            )
    except Exception:
        pass

    raise UnknownUserError(f"User id {x_demo_user_id} not found")


async def require_teacher(
    current_user: Annotated[UserOut, Depends(get_current_user)],
) -> UserOut:
    if current_user.role != UserRole.TEACHER:
        raise ForbiddenError("Only teachers can access this resource")
    return current_user


async def require_student(
    current_user: Annotated[UserOut, Depends(get_current_user)],
) -> UserOut:
    if current_user.role != UserRole.STUDENT:
        raise ForbiddenError("Only students can access this resource")
    return current_user


def verify_classroom_access(current_user: UserOut, classroom_id: int) -> None:
    """Ensures teacher or student is authorized for the requested classroom."""
    if current_user.classroom_id is None or current_user.classroom_id != classroom_id:
        raise ForbiddenError(f"User {current_user.id} not authorized to access classroom {classroom_id}")


def check_rate_limit(current_user: Annotated[UserOut, Depends(get_current_user)]) -> UserOut:
    user_rate_limiter.check(current_user.id)
    return current_user
