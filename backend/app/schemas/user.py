from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class UserRole(StrEnum):
    STUDENT = "student"
    TEACHER = "teacher"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    display_name: str
    role: UserRole
    is_simulated: bool = False
    classroom_id: int | None = None
