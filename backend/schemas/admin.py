from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from auth.roles import VALID_ROLES


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserRoleUpdate(BaseModel):
    role: str = Field(..., min_length=3, max_length=20)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        role = value.lower()
        if role not in VALID_ROLES:
            raise ValueError("Invalid user role.")
        return role


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime


class AdminLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    admin_user_id: int
    action: str
    target: str | None
    created_at: datetime

