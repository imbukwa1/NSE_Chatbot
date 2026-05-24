from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from auth.roles import ROLE_USER, VALID_ROLES


class UserRegister(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    role: str = Field(default=ROLE_USER)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        role = value.lower()
        if role not in VALID_ROLES:
            raise ValueError("Invalid user role.")
        return role


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: UserResponse


class ApiResponse(BaseModel):
    success: bool
    message: str
    data: dict
