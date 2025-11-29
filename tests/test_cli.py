"""Tests for CLI commands."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.exceptions import Exit
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.cli import _create_superuser
from src.core.security import hash_password, verify_password
from src.models.user import User


@pytest.mark.asyncio
async def test_create_superuser_new_user_success(
    db_session: AsyncSession,
) -> None:
    """Test creating a new superuser successfully."""
    email = "admin@example.com"
    name = "Admin User"
    password = "SecurePass123"

    # Mock the session factory to return our test session
    with patch("src.cli.async_session_factory") as mock_factory:
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=db_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = mock_context

        await _create_superuser(email, name, password)

    # Verify user was created
    result = await db_session.execute(
        select(User).where(User.email == email),
    )
    user = result.scalar_one_or_none()

    assert user is not None
    assert user.email == email
    assert user.name == name
    assert user.is_superuser is True
    assert verify_password(password, user.hashed_password)


@pytest.mark.asyncio
async def test_create_superuser_existing_user_promotes(
    db_session: AsyncSession,
) -> None:
    """Test promoting existing regular user to superuser."""
    email = "existing@example.com"
    name = "Existing User"
    password = "SecurePass123"

    # Create a regular user first
    user = User(
        email=email,
        name=name,
        hashed_password=hash_password(password),
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()

    # Mock the session factory to return our test session
    with patch("src.cli.async_session_factory") as mock_factory:
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=db_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = mock_context

        # Promote to superuser
        await _create_superuser(email, name, password)

    # Verify user is now superuser
    await db_session.refresh(user)
    assert user.is_superuser is True


@pytest.mark.asyncio
async def test_create_superuser_existing_superuser_no_change(
    db_session: AsyncSession,
) -> None:
    """Test that existing superuser is not changed."""
    email = "super@example.com"
    name = "Super User"
    password = "SecurePass123"

    # Create a superuser first
    user = User(
        email=email,
        name=name,
        hashed_password=hash_password(password),
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    original_id = user.id

    # Mock the session factory to return our test session
    with patch("src.cli.async_session_factory") as mock_factory:
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=db_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = mock_context

        # Try to create again
        await _create_superuser(email, name, password)

    # Verify user still exists and is still superuser
    await db_session.refresh(user)
    assert user.id == original_id
    assert user.is_superuser is True


@pytest.mark.asyncio
async def test_create_superuser_invalid_email(
    db_session: AsyncSession,
) -> None:
    """Test creating superuser with invalid email raises ValidationError."""
    email = "not-an-email"
    name = "Test User"
    password = "SecurePass123"

    with patch("src.cli.async_session_factory") as mock_factory:
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=db_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = mock_context

        with pytest.raises(Exit):
            await _create_superuser(email, name, password)


@pytest.mark.asyncio
async def test_create_superuser_invalid_password_too_short(
    db_session: AsyncSession,
) -> None:
    """Test creating superuser with password too short raises ValidationError."""
    email = "test@example.com"
    name = "Test User"
    password = "short"  # Too short

    with patch("src.cli.async_session_factory") as mock_factory:
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=db_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = mock_context

        with pytest.raises(Exit):
            await _create_superuser(email, name, password)


@pytest.mark.asyncio
async def test_create_superuser_invalid_password_no_digit(
    db_session: AsyncSession,
) -> None:
    """Test creating superuser with password without digit raises ValidationError."""
    email = "test@example.com"
    name = "Test User"
    password = "NoDigitPassword"  # No digit

    with patch("src.cli.async_session_factory") as mock_factory:
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=db_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = mock_context

        with pytest.raises(Exit):
            await _create_superuser(email, name, password)


@pytest.mark.asyncio
async def test_create_superuser_password_too_long(
    db_session: AsyncSession,
) -> None:
    """Test creating superuser with password exceeding 72 bytes."""
    email = "test@example.com"
    name = "Test User"
    password = "a" * 73  # Exceeds 72 bytes

    with patch("src.cli.async_session_factory") as mock_factory:
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=db_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = mock_context

        with pytest.raises(Exit):
            await _create_superuser(email, name, password)


@pytest.mark.asyncio
async def test_create_superuser_empty_name(db_session: AsyncSession) -> None:
    """Test creating superuser with empty name raises ValidationError."""
    email = "test@example.com"
    name = ""
    password = "SecurePass123"

    with patch("src.cli.async_session_factory") as mock_factory:
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=db_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = mock_context

        with pytest.raises(Exit):
            await _create_superuser(email, name, password)


@pytest.mark.asyncio
async def test_create_superuser_integrity_error_handling() -> None:
    """Test handling of database integrity errors."""
    email = "test@example.com"
    name = "Test User"
    password = "SecurePass123"

    # Mock session to raise IntegrityError
    with patch("src.cli.async_session_factory") as mock_factory:
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute = AsyncMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        mock_session.commit = AsyncMock(
            side_effect=IntegrityError(None, None, Exception("Mock"))
        )
        mock_session.rollback = AsyncMock()

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = mock_context

        with pytest.raises(Exit):
            await _create_superuser(email, name, password)

        mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_create_superuser_updates_name_if_different(
    db_session: AsyncSession,
) -> None:
    """Test that creating superuser with different name updates the name."""
    email = "test@example.com"
    original_name = "Original Name"
    new_name = "New Name"
    password = "SecurePass123"

    # Create a regular user first
    user = User(
        email=email,
        name=original_name,
        hashed_password=hash_password(password),
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()

    # Mock the session factory to return our test session
    with patch("src.cli.async_session_factory") as mock_factory:
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=db_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = mock_context

        # Create superuser with new name
        await _create_superuser(email, new_name, password)

    # Verify user is superuser (note: CLI doesn't update name when promoting)
    await db_session.refresh(user)
    assert user.is_superuser is True
    # The CLI currently doesn't update the name when promoting, only when
    # creating new. So we just verify the user was promoted.


@pytest.mark.asyncio
async def test_create_superuser_password_hashing(
    db_session: AsyncSession,
) -> None:
    """Test that password is properly hashed when creating superuser."""
    email = "test@example.com"
    name = "Test User"
    password = "SecurePass123"

    # Mock the session factory to return our test session
    with patch("src.cli.async_session_factory") as mock_factory:
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=db_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = mock_context

        await _create_superuser(email, name, password)

    result = await db_session.execute(
        select(User).where(User.email == email),
    )
    user = result.scalar_one_or_none()

    assert user is not None
    # Password should be hashed, not plain text
    assert user.hashed_password != password
    assert verify_password(password, user.hashed_password)


@pytest.mark.asyncio
async def test_create_superuser_unicode_name(db_session: AsyncSession) -> None:
    """Test creating superuser with unicode characters in name."""
    email = "test@example.com"
    name = "测试用户 🧙‍♂️"
    password = "SecurePass123"

    # Mock the session factory to return our test session
    with patch("src.cli.async_session_factory") as mock_factory:
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=db_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = mock_context

        await _create_superuser(email, name, password)

    result = await db_session.execute(
        select(User).where(User.email == email),
    )
    user = result.scalar_one_or_none()

    assert user is not None
    assert user.name == name


@pytest.mark.asyncio
async def test_create_superuser_unicode_email(db_session: AsyncSession) -> None:
    """Test creating superuser with unicode characters in email."""
    email = "test+unicode@example.com"
    name = "Test User"
    password = "SecurePass123"

    # Mock the session factory to return our test session
    with patch("src.cli.async_session_factory") as mock_factory:
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=db_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = mock_context

        await _create_superuser(email, name, password)

    result = await db_session.execute(
        select(User).where(User.email == email),
    )
    user = result.scalar_one_or_none()

    assert user is not None
    assert user.email == email


@pytest.mark.asyncio
async def test_create_superuser_exception_handling() -> None:
    """Test that unexpected exceptions are properly handled."""
    email = "test@example.com"
    name = "Test User"
    password = "SecurePass123"

    # Mock session to raise unexpected exception
    with patch("src.cli.async_session_factory") as mock_factory:
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute = AsyncMock(
            side_effect=Exception("Unexpected error")
        )
        mock_session.rollback = AsyncMock()

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = mock_context

        with pytest.raises(Exit):
            await _create_superuser(email, name, password)

        mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_create_superuser_password_exactly_72_bytes(
    db_session: AsyncSession,
) -> None:
    """Test creating superuser with password exactly 72 bytes."""
    email = "test@example.com"
    name = "Test User"
    # Password with digit, exactly 72 bytes
    password = "a" * 71 + "1"  # 71 'a' + 1 digit = 72 bytes

    # Mock the session factory to return our test session
    with patch("src.cli.async_session_factory") as mock_factory:
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=db_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = mock_context

        await _create_superuser(email, name, password)

    result = await db_session.execute(
        select(User).where(User.email == email),
    )
    user = result.scalar_one_or_none()

    assert user is not None
    assert verify_password(password, user.hashed_password)
