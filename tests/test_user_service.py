"""Tests for user service."""

import uuid

import pytest
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import verify_password
from src.schemas.user import UserCreate, UserUpdate
from src.services.user_service import (
    UserAlreadyDeletedError,
    UserAlreadyExistsError,
    UserNotFoundError,
    UserService,
)


@pytest.mark.asyncio
async def test_create_user_success(db_session: AsyncSession) -> None:
    """Test successful user creation."""
    user_service = UserService(db_session)
    user_data = UserCreate(
        name="Test User",
        email="test@example.com",
        password=SecretStr("SecurePass123"),
    )

    user = await user_service.create_user(user_data)

    assert user.id is not None
    assert user.name == "Test User"
    assert user.email == "test@example.com"
    assert user.hashed_password != "SecurePass123"  # Should be hashed
    assert verify_password("SecurePass123", user.hashed_password)
    assert user.is_deleted is False
    assert user.is_superuser is False
    assert user.created_at is not None


@pytest.mark.asyncio
async def test_create_user_duplicate_email(db_session: AsyncSession) -> None:
    """Test creating user with duplicate email fails."""
    user_service = UserService(db_session)
    user_data = UserCreate(
        name="Test User",
        email="test@example.com",
        password=SecretStr("SecurePass123"),
    )

    # Create first user
    await user_service.create_user(user_data)

    # Try to create duplicate
    with pytest.raises(UserAlreadyExistsError) as exc_info:
        await user_service.create_user(user_data)

    assert "already exists" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_get_user_by_id_success(db_session: AsyncSession) -> None:
    """Test getting user by ID when user exists."""
    user_service = UserService(db_session)
    user_data = UserCreate(
        name="Test User",
        email="test@example.com",
        password=SecretStr("SecurePass123"),
    )

    created_user = await user_service.create_user(user_data)
    found_user = await user_service.get_user_by_id(created_user.id)

    assert found_user is not None
    assert found_user.id == created_user.id
    assert found_user.email == "test@example.com"
    assert found_user.name == "Test User"


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(db_session: AsyncSession) -> None:
    """Test getting user by ID when user doesn't exist."""
    user_service = UserService(db_session)
    non_existent_id = uuid.uuid4()

    found_user = await user_service.get_user_by_id(non_existent_id)

    assert found_user is None


@pytest.mark.asyncio
async def test_get_user_by_email_success(db_session: AsyncSession) -> None:
    """Test getting user by email when user exists."""
    user_service = UserService(db_session)
    user_data = UserCreate(
        name="Test User",
        email="test@example.com",
        password=SecretStr("SecurePass123"),
    )

    await user_service.create_user(user_data)
    found_user = await user_service.get_user_by_email("test@example.com")

    assert found_user is not None
    assert found_user.email == "test@example.com"
    assert found_user.name == "Test User"


@pytest.mark.asyncio
async def test_get_user_by_email_not_found(db_session: AsyncSession) -> None:
    """Test getting user by email when user doesn't exist."""
    user_service = UserService(db_session)

    found_user = await user_service.get_user_by_email(
        "nonexistent@example.com"
    )

    assert found_user is None


@pytest.mark.asyncio
async def test_update_user_success(db_session: AsyncSession) -> None:
    """Test successful user update."""
    user_service = UserService(db_session)
    user_data = UserCreate(
        name="Test User",
        email="test@example.com",
        password=SecretStr("SecurePass123"),
    )

    created_user = await user_service.create_user(user_data)
    update_data = UserUpdate(
        name="Updated Name",
        is_superuser=True,
        email=None,
        password=None,
    )

    updated_user = await user_service.update_user(created_user.id, update_data)

    assert updated_user.name == "Updated Name"
    assert updated_user.is_superuser is True
    assert updated_user.email == "test@example.com"  # Unchanged


@pytest.mark.asyncio
async def test_update_user_partial(db_session: AsyncSession) -> None:
    """Test partial user update."""
    user_service = UserService(db_session)
    user_data = UserCreate(
        name="Test User",
        email="test@example.com",
        password=SecretStr("SecurePass123"),
    )

    created_user = await user_service.create_user(user_data)
    update_data = UserUpdate(
        name="Updated Name",
        email=None,
        password=None,
        is_superuser=None,
    )

    updated_user = await user_service.update_user(created_user.id, update_data)

    assert updated_user.name == "Updated Name"
    assert updated_user.email == "test@example.com"  # Unchanged
    assert updated_user.is_superuser is False  # Unchanged


@pytest.mark.asyncio
async def test_update_user_not_found(db_session: AsyncSession) -> None:
    """Test updating non-existent user fails."""
    user_service = UserService(db_session)
    non_existent_id = uuid.uuid4()
    update_data = UserUpdate(
        name="Updated Name",
        email=None,
        password=None,
        is_superuser=None,
    )

    with pytest.raises(UserNotFoundError) as exc_info:
        await user_service.update_user(non_existent_id, update_data)

    assert "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_update_user_duplicate_email(db_session: AsyncSession) -> None:
    """Test updating user with duplicate email fails."""
    user_service = UserService(db_session)

    # Create two users
    user1_data = UserCreate(
        name="User 1",
        email="user1@example.com",
        password=SecretStr("SecurePass123"),
    )
    user2_data = UserCreate(
        name="User 2",
        email="user2@example.com",
        password=SecretStr("SecurePass123"),
    )

    user1 = await user_service.create_user(user1_data)
    await user_service.create_user(user2_data)

    # Try to update user1 with user2's email
    update_data = UserUpdate(
        email="user2@example.com",
        name=None,
        password=None,
        is_superuser=None,
    )

    with pytest.raises(UserAlreadyExistsError) as exc_info:
        await user_service.update_user(user1.id, update_data)

    assert "already exists" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_update_user_same_email(db_session: AsyncSession) -> None:
    """Test updating user with same email succeeds."""
    user_service = UserService(db_session)
    user_data = UserCreate(
        name="Test User",
        email="test@example.com",
        password=SecretStr("SecurePass123"),
    )

    created_user = await user_service.create_user(user_data)
    update_data = UserUpdate(
        email="test@example.com",
        name="Updated Name",
        password=None,
        is_superuser=None,
    )

    updated_user = await user_service.update_user(created_user.id, update_data)

    assert updated_user.email == "test@example.com"
    assert updated_user.name == "Updated Name"


@pytest.mark.asyncio
async def test_delete_user_soft_delete(db_session: AsyncSession) -> None:
    """Test soft deleting a user."""
    user_service = UserService(db_session)
    user_data = UserCreate(
        name="Test User",
        email="test@example.com",
        password=SecretStr("SecurePass123"),
    )

    created_user = await user_service.create_user(user_data)
    result = await user_service.delete_user(created_user.id, hard_delete=False)

    assert result is True

    # Verify soft delete
    await db_session.refresh(created_user)
    assert created_user.is_deleted is True
    assert created_user.deleted_at is not None

    # User should not be found in normal queries
    found_user = await user_service.get_user_by_id(created_user.id)
    assert found_user is not None  # Still exists in DB
    assert found_user.is_deleted is True


@pytest.mark.asyncio
async def test_delete_user_hard_delete(db_session: AsyncSession) -> None:
    """Test hard deleting a user."""
    user_service = UserService(db_session)
    user_data = UserCreate(
        name="Test User",
        email="test@example.com",
        password=SecretStr("SecurePass123"),
    )

    created_user = await user_service.create_user(user_data)
    user_id = created_user.id
    result = await user_service.delete_user(user_id, hard_delete=True)

    assert result is True

    # User should not be found
    found_user = await user_service.get_user_by_id(user_id)
    assert found_user is None


@pytest.mark.asyncio
async def test_delete_user_not_found(db_session: AsyncSession) -> None:
    """Test deleting non-existent user fails."""
    user_service = UserService(db_session)
    non_existent_id = uuid.uuid4()

    with pytest.raises(UserNotFoundError) as exc_info:
        await user_service.delete_user(non_existent_id)

    assert "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_delete_user_already_deleted(db_session: AsyncSession) -> None:
    """Test deleting already soft-deleted user fails."""
    user_service = UserService(db_session)
    user_data = UserCreate(
        name="Test User",
        email="test@example.com",
        password=SecretStr("SecurePass123"),
    )

    created_user = await user_service.create_user(user_data)
    await user_service.delete_user(created_user.id, hard_delete=False)

    # Try to delete again
    with pytest.raises(UserAlreadyDeletedError) as exc_info:
        await user_service.delete_user(created_user.id, hard_delete=False)

    assert "already deleted" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_list_users_empty(db_session: AsyncSession) -> None:
    """Test listing users when no users exist."""
    user_service = UserService(db_session)

    users, total = await user_service.list_users()

    assert users == []
    assert total == 0


@pytest.mark.asyncio
async def test_list_users_pagination(db_session: AsyncSession) -> None:
    """Test listing users with pagination."""
    user_service = UserService(db_session)

    # Create 5 users
    for i in range(5):
        user_data = UserCreate(
            name=f"User {i}",
            email=f"user{i}@example.com",
            password=SecretStr("SecurePass123"),
        )
        await user_service.create_user(user_data)

    # Get first page
    users_page1, total = await user_service.list_users(page=1, page_size=2)

    assert len(users_page1) == 2
    assert total == 5

    # Get second page
    users_page2, total = await user_service.list_users(page=2, page_size=2)

    assert len(users_page2) == 2
    assert total == 5

    # Verify different users
    assert users_page1[0].id != users_page2[0].id


@pytest.mark.asyncio
async def test_list_users_exclude_deleted(db_session: AsyncSession) -> None:
    """Test listing users excludes deleted users by default."""
    user_service = UserService(db_session)

    # Create 3 users
    user1_data = UserCreate(
        name="User 1",
        email="user1@example.com",
        password=SecretStr("SecurePass123"),
    )
    user2_data = UserCreate(
        name="User 2",
        email="user2@example.com",
        password=SecretStr("SecurePass123"),
    )
    user3_data = UserCreate(
        name="User 3",
        email="user3@example.com",
        password=SecretStr("SecurePass123"),
    )

    user1 = await user_service.create_user(user1_data)
    await user_service.create_user(user2_data)
    await user_service.create_user(user3_data)

    # Delete one user
    await user_service.delete_user(user1.id, hard_delete=False)

    # List users (should exclude deleted)
    users, total = await user_service.list_users(include_deleted=False)

    assert len(users) == 2
    assert total == 2
    assert all(not user.is_deleted for user in users)


@pytest.mark.asyncio
async def test_list_users_include_deleted(db_session: AsyncSession) -> None:
    """Test listing users includes deleted users when requested."""
    user_service = UserService(db_session)

    # Create 2 users
    user1_data = UserCreate(
        name="User 1",
        email="user1@example.com",
        password=SecretStr("SecurePass123"),
    )
    user2_data = UserCreate(
        name="User 2",
        email="user2@example.com",
        password=SecretStr("SecurePass123"),
    )

    user1 = await user_service.create_user(user1_data)
    await user_service.create_user(user2_data)

    # Delete one user
    await user_service.delete_user(user1.id, hard_delete=False)

    # List users (should include deleted)
    users, total = await user_service.list_users(include_deleted=True)

    assert len(users) == 2
    assert total == 2
    assert any(user.is_deleted for user in users)


@pytest.mark.asyncio
async def test_verify_user_password_success(db_session: AsyncSession) -> None:
    """Test verifying correct password."""
    user_service = UserService(db_session)
    password = "SecurePass123"
    user_data = UserCreate(
        name="Test User",
        email="test@example.com",
        password=SecretStr(password),
    )

    created_user = await user_service.create_user(user_data)
    verified_user = await user_service.verify_user_password(
        "test@example.com",
        password,
    )

    assert verified_user is not None
    assert verified_user.id == created_user.id
    assert verified_user.email == "test@example.com"


@pytest.mark.asyncio
async def test_verify_user_password_wrong_password(
    db_session: AsyncSession,
) -> None:
    """Test verifying wrong password returns None."""
    user_service = UserService(db_session)
    user_data = UserCreate(
        name="Test User",
        email="test@example.com",
        password=SecretStr("SecurePass123"),
    )

    await user_service.create_user(user_data)
    verified_user = await user_service.verify_user_password(
        "test@example.com",
        "WrongPassword123",
    )

    assert verified_user is None


@pytest.mark.asyncio
async def test_verify_user_password_user_not_found(
    db_session: AsyncSession,
) -> None:
    """Test verifying password for non-existent user returns None."""
    user_service = UserService(db_session)

    verified_user = await user_service.verify_user_password(
        "nonexistent@example.com",
        "SecurePass123",
    )

    assert verified_user is None


@pytest.mark.asyncio
async def test_user_exists_true(db_session: AsyncSession) -> None:
    """Test user_exists returns True when user exists."""
    user_service = UserService(db_session)
    user_data = UserCreate(
        name="Test User",
        email="test@example.com",
        password=SecretStr("SecurePass123"),
    )

    await user_service.create_user(user_data)
    exists = await user_service.user_exists("test@example.com")

    assert exists is True


@pytest.mark.asyncio
async def test_user_exists_false(db_session: AsyncSession) -> None:
    """Test user_exists returns False when user doesn't exist."""
    user_service = UserService(db_session)

    exists = await user_service.user_exists("nonexistent@example.com")

    assert exists is False
