"""Auth API."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import oauth2_scheme
from src.database.database import get_async_session
from src.models.user import User
from src.schemas.user import (
    Token,
    TokenValidationResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from src.services.auth_service import (
    AuthService,
    InvalidCredentialsError,
    TokenValidationError,
)
from src.services.user_service import UserAlreadyExistsError


router = APIRouter()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_session),
) -> User:
    """Get the current user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        auth_service = AuthService(db)
        return await auth_service.get_user_from_token(token)
    except TokenValidationError as e:
        raise credentials_exception from e


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> User:
    """Register a new user."""
    try:
        auth_service = AuthService(db)
        return await auth_service.register_user(user_data)
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/token", response_model=Token)
async def login(
    user_data: UserLogin,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> Token:
    """Login a user."""
    try:
        auth_service = AuthService(db)
        return await auth_service.login(user_data)
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


@router.get("/validate-token", response_model=TokenValidationResponse)
async def validate_token(
    current_user: Annotated[User, Depends(get_current_user)],
) -> TokenValidationResponse:
    """Validate token."""
    return TokenValidationResponse(valid=True, user_id=str(current_user.id))


@router.get("/users/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current user information."""
    return current_user
