from enum import StrEnum

from pydantic import BaseModel, EmailStr, Field


class AuthUserRole(StrEnum):
    CANDIDATE = "candidate"
    HR = "hr"
    ADMIN = "admin"


class UserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=6, max_length=128)
    role: AuthUserRole


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: AuthUserRole
    is_active: bool


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse