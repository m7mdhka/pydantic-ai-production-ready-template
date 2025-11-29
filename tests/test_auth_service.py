"""Tests for auth service."""

from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.security import hash_password
from src.models.user import User
from src.schemas.user import UserCreate, UserLogin
from src.services.auth_service import (
    AuthService,
    InvalidCredentialsError,
    TokenValidationError,
)
from src.services.user_service import UserAlreadyExistsError


@pytest.mark.asyncio
async def test_register_user_success(db_session: AsyncSession) -> None:
    """Test successful user registration."""
    auth_service = AuthService(db_session)

    user_data = UserCreate(
        name="Test User",
        email="test@example.com",
        password=SecretStr("SecurePass123"),
    )

    user = await auth_service.register_user(user_data)

    assert user.id is not None
    assert user.name == "Test User"
    assert user.email == "test@example.com"
    assert user.is_deleted is False


@pytest.mark.asyncio
async def test_register_user_duplicate_email(db_session: AsyncSession) -> None:
    """Test registration with duplicate email raises error."""
    auth_service = AuthService(db_session)

    user_data = UserCreate(
        name="Test User",
        email="test@example.com",
        password=SecretStr("SecurePass123"),
    )

    # Create first user
    await auth_service.register_user(user_data)

    # Try to register again with same email
    with pytest.raises(UserAlreadyExistsError):
        await auth_service.register_user(user_data)


@pytest.mark.asyncio
async def test_authenticate_user_success(db_session: AsyncSession) -> None:
    """Test successful user authentication."""
    auth_service = AuthService(db_session)

    # Create a user first
    password = "SecurePass123"
    user = User(
        name="Test User",
        email="test@example.com",
        hashed_password=hash_password(password),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Authenticate
    user_data = UserLogin(
        email="test@example.com",
        password=SecretStr(password),
    )
    authenticated_user = await auth_service.authenticate_user(user_data)

    assert authenticated_user.id == user.id
    assert authenticated_user.email == user.email


@pytest.mark.asyncio
async def test_authenticate_user_invalid_email(
    db_session: AsyncSession,
) -> None:
    """Test authentication with non-existent email fails."""
    auth_service = AuthService(db_session)

    user_data = UserLogin(
        email="nonexistent@example.com",
        password=SecretStr("SecurePass123"),
    )

    with pytest.raises(InvalidCredentialsError):
        await auth_service.authenticate_user(user_data)


@pytest.mark.asyncio
async def test_authenticate_user_invalid_password(
    db_session: AsyncSession,
) -> None:
    """Test authentication with incorrect password fails."""
    auth_service = AuthService(db_session)

    # Create a user first
    password = "SecurePass123"
    user = User(
        name="Test User",
        email="test@example.com",
        hashed_password=hash_password(password),
    )
    db_session.add(user)
    await db_session.commit()

    # Try to authenticate with wrong password
    user_data = UserLogin(
        email="test@example.com",
        password=SecretStr("WrongPassword123"),
    )

    with pytest.raises(InvalidCredentialsError):
        await auth_service.authenticate_user(user_data)


@pytest.mark.asyncio
async def test_create_token_success(db_session: AsyncSession) -> None:
    """Test successful token creation."""
    auth_service = AuthService(db_session)

    user = User(
        name="Test User",
        email="test@example.com",
        hashed_password=hash_password("SecurePass123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = auth_service.create_token(user)

    assert token.access_token is not None
    assert token.token_type == "Bearer"
    assert len(token.access_token) > 0

    # Verify token can be decoded
    payload = jwt.decode(
        token.access_token,
        # pylint: disable=no-member
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
    )
    assert payload["sub"] == user.email
    assert "exp" in payload


@pytest.mark.asyncio
async def test_create_token_with_custom_expires_delta(
    db_session: AsyncSession,
) -> None:
    """Test token creation with custom expiration time."""
    auth_service = AuthService(db_session)

    user = User(
        name="Test User",
        email="test@example.com",
        hashed_password=hash_password("SecurePass123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    custom_delta = timedelta(minutes=60)
    token = auth_service.create_token(user, expires_delta=custom_delta)

    # Verify token can be decoded
    payload = jwt.decode(
        token.access_token,
        # pylint: disable=no-member
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
    )
    assert payload["sub"] == user.email

    # Check expiration is approximately 60 minutes from now
    exp_timestamp = payload["exp"]

    expected_exp = datetime.now(UTC) + custom_delta
    actual_exp = datetime.fromtimestamp(exp_timestamp, tz=UTC)
    # Allow 5 second tolerance
    assert abs((actual_exp - expected_exp).total_seconds()) < 5


@pytest.mark.asyncio
async def test_login_success(db_session: AsyncSession) -> None:
    """Test successful login."""
    auth_service = AuthService(db_session)

    # Create a user first
    password = "SecurePass123"
    user = User(
        name="Test User",
        email="test@example.com",
        hashed_password=hash_password(password),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Login
    user_data = UserLogin(
        email="test@example.com",
        password=SecretStr(password),
    )
    token = await auth_service.login(user_data)

    assert token.access_token is not None
    assert token.token_type == "Bearer"

    # Verify token contains correct email
    payload = jwt.decode(
        token.access_token,
        # pylint: disable=no-member
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
    )
    assert payload["sub"] == user.email


@pytest.mark.asyncio
async def test_login_invalid_credentials(db_session: AsyncSession) -> None:
    """Test login with invalid credentials fails."""
    auth_service = AuthService(db_session)

    user_data = UserLogin(
        email="nonexistent@example.com",
        password=SecretStr("SecurePass123"),
    )

    with pytest.raises(InvalidCredentialsError):
        await auth_service.login(user_data)


@pytest.mark.asyncio
async def test_get_user_from_token_success(db_session: AsyncSession) -> None:
    """Test getting user from valid token."""
    auth_service = AuthService(db_session)

    # Create a user
    user = User(
        name="Test User",
        email="test@example.com",
        hashed_password=hash_password("SecurePass123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create a token
    token = auth_service.create_token(user)

    # Get user from token
    retrieved_user = await auth_service.get_user_from_token(token.access_token)

    assert retrieved_user.id == user.id
    assert retrieved_user.email == user.email
    assert retrieved_user.name == user.name


@pytest.mark.asyncio
async def test_get_user_from_token_invalid_token(
    db_session: AsyncSession,
) -> None:
    """Test getting user from invalid token fails."""
    auth_service = AuthService(db_session)

    invalid_token = "invalid.token.here"

    with pytest.raises(TokenValidationError):
        await auth_service.get_user_from_token(invalid_token)


@pytest.mark.asyncio
async def test_get_user_from_token_missing_subject(
    db_session: AsyncSession,
) -> None:
    """Test getting user from token without subject fails."""
    auth_service = AuthService(db_session)

    # Create a token without 'sub' field
    token_without_sub = jwt.encode(
        {"exp": 9999999999},  # Far future expiration
        # pylint: disable=no-member
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(TokenValidationError) as exc_info:
        await auth_service.get_user_from_token(token_without_sub)

    assert "Token missing subject" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_user_from_token_user_not_found(
    db_session: AsyncSession,
) -> None:
    """Test getting user from token when user doesn't exist."""
    auth_service = AuthService(db_session)

    # Create a token for a non-existent user
    token_for_nonexistent = jwt.encode(
        {"sub": "nonexistent@example.com", "exp": 9999999999},
        # pylint: disable=no-member
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(TokenValidationError) as exc_info:
        await auth_service.get_user_from_token(token_for_nonexistent)

    assert "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_get_user_from_token_expired_token(
    db_session: AsyncSession,
) -> None:
    """Test getting user from expired token fails."""
    auth_service = AuthService(db_session)

    # Create an expired token
    expired_token = jwt.encode(
        {
            "sub": "test@example.com",
            # Expired 1 hour ago
            "exp": datetime.now(UTC) - timedelta(hours=1),
        },
        # pylint: disable=no-member
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(TokenValidationError):
        await auth_service.get_user_from_token(expired_token)


@pytest.mark.asyncio
async def test_validate_token_success(db_session: AsyncSession) -> None:
    """Test token validation with valid token."""
    auth_service = AuthService(db_session)

    # Create a user
    user = User(
        name="Test User",
        email="test@example.com",
        hashed_password=hash_password("SecurePass123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create a token
    token = auth_service.create_token(user)

    # Validate token
    is_valid, retrieved_user = await auth_service.validate_token(
        token.access_token
    )

    assert is_valid is True
    assert retrieved_user is not None
    assert retrieved_user.id == user.id
    assert retrieved_user.email == user.email


@pytest.mark.asyncio
async def test_validate_token_invalid_token(db_session: AsyncSession) -> None:
    """Test token validation with invalid token."""
    auth_service = AuthService(db_session)

    invalid_token = "invalid.token.here"

    is_valid, user = await auth_service.validate_token(invalid_token)

    assert is_valid is False
    assert user is None


@pytest.mark.asyncio
async def test_validate_token_expired_token(db_session: AsyncSession) -> None:
    """Test token validation with expired token."""
    auth_service = AuthService(db_session)

    # Create an expired token
    expired_token = jwt.encode(
        {
            "sub": "test@example.com",
            "exp": datetime.now(UTC) - timedelta(hours=1),
        },
        # pylint: disable=no-member
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

    is_valid, user = await auth_service.validate_token(expired_token)

    assert is_valid is False
    assert user is None


@pytest.mark.asyncio
async def test_validate_token_user_not_found(db_session: AsyncSession) -> None:
    """Test token validation when user doesn't exist."""
    auth_service = AuthService(db_session)

    # Create a token for non-existent user
    token_for_nonexistent = jwt.encode(
        {"sub": "nonexistent@example.com", "exp": 9999999999},
        # pylint: disable=no-member
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

    is_valid, user = await auth_service.validate_token(token_for_nonexistent)

    assert is_valid is False
    assert user is None
