"""Tests for authentication endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import hash_password
from src.models.user import User


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient, db_session: AsyncSession) -> None:
    """Test successful user registration."""
    user_data = {
        "name": "Test User",
        "email": "test@example.com",
        "password": "SecurePass123",
    }

    response = await client.post("/v1/auth/register", json=user_data)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"
    assert "id" in data
    assert "hashed_password" not in data
    assert "password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test registration with duplicate email fails."""
    user_data = {
        "name": "Test User",
        "email": "test@example.com",
        "password": "SecurePass123",
    }

    # Create first user
    await client.post("/v1/auth/register", json=user_data)

    # Try to register again with same email
    response = await client.post("/v1/auth/register", json=user_data)

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_invalid_password(client: AsyncClient) -> None:
    """Test registration with invalid password fails."""
    user_data = {
        "name": "Test User",
        "email": "test@example.com",
        "password": "short",  # Too short
    }

    response = await client.post("/v1/auth/register", json=user_data)

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient) -> None:
    """Test registration with invalid email fails."""
    user_data = {
        "name": "Test User",
        "email": "not-an-email",
        "password": "SecurePass123",
    }

    response = await client.post("/v1/auth/register", json=user_data)

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_login_success(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test successful user login."""
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
    login_data = {
        "email": "test@example.com",
        "password": password,
    }

    response = await client.post("/v1/auth/token", json=login_data)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 0


@pytest.mark.asyncio
async def test_login_invalid_email(client: AsyncClient) -> None:
    """Test login with non-existent email fails."""
    login_data = {
        "email": "nonexistent@example.com",
        "password": "SecurePass123",
    }

    response = await client.post("/v1/auth/token", json=login_data)

    assert response.status_code == 401
    assert "incorrect email or password" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_invalid_password(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test login with incorrect password fails."""
    # Create a user first
    user = User(
        name="Test User",
        email="test@example.com",
        hashed_password=hash_password("SecurePass123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Try to login with wrong password
    login_data = {
        "email": "test@example.com",
        "password": "WrongPassword123",
    }

    response = await client.post("/v1/auth/token", json=login_data)

    assert response.status_code == 401
    assert "incorrect email or password" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_validate_token_success(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test token validation with valid token."""
    # Create a user and get a token
    password = "SecurePass123"
    user = User(
        name="Test User",
        email="test@example.com",
        hashed_password=hash_password(password),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Login to get token
    login_data = {
        "email": "test@example.com",
        "password": password,
    }
    login_response = await client.post("/v1/auth/token", json=login_data)
    token = login_response.json()["access_token"]

    # Validate token
    response = await client.get(
        "/v1/auth/validate-token",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["user_id"] == str(user.id)


@pytest.mark.asyncio
async def test_validate_token_missing_header(client: AsyncClient) -> None:
    """Test token validation without authorization header fails."""
    response = await client.get("/v1/auth/validate-token")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_validate_token_invalid_token(client: AsyncClient) -> None:
    """Test token validation with invalid token fails."""
    response = await client.get(
        "/v1/auth/validate-token",
        headers={"Authorization": "Bearer invalid_token_here"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_success(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test getting current user info with valid token."""
    # Create a user and get a token
    password = "SecurePass123"
    user = User(
        name="Test User",
        email="test@example.com",
        hashed_password=hash_password(password),
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Login to get token
    login_data = {
        "email": "test@example.com",
        "password": password,
    }
    login_response = await client.post("/v1/auth/token", json=login_data)
    token = login_response.json()["access_token"]

    # Get current user info
    response = await client.get(
        "/v1/auth/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"
    assert data["id"] == str(user.id)
    assert data["is_superuser"] is False
    assert "hashed_password" not in data
    assert "password" not in data


@pytest.mark.asyncio
async def test_get_current_user_missing_token(client: AsyncClient) -> None:
    """Test getting current user without token fails."""
    response = await client.get("/v1/auth/users/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(client: AsyncClient) -> None:
    """Test getting current user with invalid token fails."""
    response = await client.get(
        "/v1/auth/users/me",
        headers={"Authorization": "Bearer invalid_token_here"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_empty_name(client: AsyncClient) -> None:
    """Test registration with empty name fails."""
    user_data = {
        "name": "",
        "email": "test@example.com",
        "password": "SecurePass123",
    }

    response = await client.post("/v1/auth/register", json=user_data)

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_register_password_no_digit(client: AsyncClient) -> None:
    """Test registration with password without digit fails."""
    user_data = {
        "name": "Test User",
        "email": "test@example.com",
        "password": "NoDigitPassword",
    }

    response = await client.post("/v1/auth/register", json=user_data)

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_login_missing_fields(client: AsyncClient) -> None:
    """Test login with missing fields fails."""
    # Missing password
    response = await client.post(
        "/v1/auth/token",
        json={"email": "test@example.com"},
    )
    assert response.status_code == 422

    # Missing email
    response = await client.post(
        "/v1/auth/token",
        json={"password": "SecurePass123"},
    )
    assert response.status_code == 422
