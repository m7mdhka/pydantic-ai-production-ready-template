"""User schemas."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, SecretStr


MIN_PASSWORD_LENGTH = 8


class PasswordStrengthError(ValueError):
    """Exception for password strength errors."""


def validate_password_complexity(v: SecretStr) -> SecretStr:
    """Validate password complexity."""
    value = v.get_secret_value()
    if not any(char.isdigit() for char in value):
        msg = "Password must contain a number"
        raise PasswordStrengthError(msg)
    if len(value) < MIN_PASSWORD_LENGTH:
        msg = "Password is too short (min 8)"
        raise PasswordStrengthError(msg)
    return v


PasswordStr = Annotated[
    SecretStr,
    AfterValidator(validate_password_complexity),
]


class UserBase(BaseModel):
    """Base user schema."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="User's full name",
    )
    email: EmailStr = Field(..., description="User's email address")


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: PasswordStr = Field(
        ...,
        max_length=100,
        description="User's password",
    )


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    name: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="User's full name",
    )
    email: EmailStr | None = Field(None, description="User's email address")
    password: PasswordStr | None = Field(
        None,
        max_length=100,
        description="User's password",
    )
    is_superuser: bool | None = Field(
        None,
        description="Whether the user is a superuser",
    )


class UserResponse(UserBase):
    """Schema for user response."""

    id: uuid.UUID = Field(..., description="User's unique identifier")
    created_at: datetime = Field(..., description="User creation timestamp")
    updated_at: datetime | None = Field(
        None,
        description="User last update timestamp",
    )
    is_superuser: bool = Field(
        ...,
        description="Whether the user is a superuser",
    )

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """Schema for paginated user list response."""

    users: list[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr = Field(..., description="User's email address")
    password: SecretStr = Field(..., description="User's password")


class Token(BaseModel):
    """Schema for token response."""

    access_token: str = Field(..., description="Access token")
    token_type: str = Field(..., description="Token type")
