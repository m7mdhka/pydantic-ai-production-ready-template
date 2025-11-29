"""Tests for security utilities."""

from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt
from jwt.exceptions import ExpiredSignatureError

from src.core.config import settings
from src.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)


class TestHashPassword:
    """Tests for password hashing."""

    def test_hash_password_returns_string(self) -> None:
        """Test that hash_password returns a string."""
        password = "TestPassword123"
        hashed = hash_password(password)
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_produces_different_hashes(self) -> None:
        """Test that same password produces different hashes (due to salt)."""
        password = "TestPassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        # Hashes should be different due to random salt
        assert hash1 != hash2

    def test_hash_password_handles_special_characters(self) -> None:
        """Test that hash_password handles special characters."""
        password = "P@ssw0rd!#$%^&*()"
        hashed = hash_password(password)
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_handles_unicode(self) -> None:
        """Test that hash_password handles unicode characters."""
        password = "Pässwörd测试123"
        hashed = hash_password(password)
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_handles_empty_string(self) -> None:
        """Test that hash_password handles empty string."""
        password = ""
        hashed = hash_password(password)
        assert isinstance(hashed, str)
        assert len(hashed) > 0


class TestVerifyPassword:
    """Tests for password verification."""

    def test_verify_password_correct_password(self) -> None:
        """Test that verify_password returns True for correct password."""
        password = "TestPassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect_password(self) -> None:
        """Test that verify_password returns False for incorrect password."""
        password = "TestPassword123"
        wrong_password = "WrongPassword123"
        hashed = hash_password(password)
        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty_password(self) -> None:
        """Test that verify_password handles empty password."""
        password = ""
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
        assert verify_password("not_empty", hashed) is False

    def test_verify_password_case_sensitive(self) -> None:
        """Test that verify_password is case sensitive."""
        password = "TestPassword123"
        hashed = hash_password(password)
        assert verify_password("testpassword123", hashed) is False
        assert verify_password("TestPassword123", hashed) is True

    def test_verify_password_special_characters(self) -> None:
        """Test that verify_password handles special characters correctly."""
        password = "P@ssw0rd!#$%^&*()"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
        assert verify_password("P@ssw0rd!#$%^&*()", hashed) is True

    def test_verify_password_unicode(self) -> None:
        """Test that verify_password handles unicode characters."""
        password = "Pässwörd测试123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
        assert verify_password("different", hashed) is False

    def test_verify_password_with_different_hashes(self) -> None:
        """Test verify_password works with different hashes of same password."""
        password = "TestPassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        # Both hashes should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestCreateAccessToken:
    """Tests for JWT token creation."""

    def test_create_access_token_returns_string(self) -> None:
        """Test that create_access_token returns a string."""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_custom_expires_delta(self) -> None:
        """Test that create_access_token respects custom expiration."""
        data = {"sub": "test@example.com"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta=expires_delta)

        # Decode and verify expiration
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),  # pylint: disable=no-member
            algorithms=[settings.jwt_algorithm],
        )
        exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        now = datetime.now(UTC)
        # Should expire in approximately 30 minutes
        # (allow 1 minute tolerance)
        assert 29 * 60 <= (exp - now).total_seconds() <= 31 * 60

    def test_create_access_token_default_expiration(self) -> None:
        """
        Test that create_access_token uses default expiration when not
        specified.
        """
        data = {"sub": "test@example.com"}
        token = create_access_token(data)

        # Decode and verify expiration
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),  # pylint: disable=no-member
            algorithms=[settings.jwt_algorithm],
        )
        exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        now = datetime.now(UTC)
        # Should expire in approximately 15 minutes (default)
        assert 14 * 60 <= (exp - now).total_seconds() <= 16 * 60

    def test_create_access_token_contains_data(self) -> None:
        """Test that create_access_token includes the provided data."""
        data = {"sub": "test@example.com", "user_id": "123"}
        token = create_access_token(data)

        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),  # pylint: disable=no-member
            algorithms=[settings.jwt_algorithm],
        )
        assert payload["sub"] == "test@example.com"
        assert payload["user_id"] == "123"
        assert "exp" in payload

    def test_create_access_token_includes_expiration(self) -> None:
        """Test that create_access_token includes expiration claim."""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)

        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),  # pylint: disable=no-member
            algorithms=[settings.jwt_algorithm],
        )
        assert "exp" in payload
        assert isinstance(payload["exp"], int)

    def test_create_access_token_uses_correct_algorithm(self) -> None:
        """Test that create_access_token uses the configured algorithm."""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)

        # Should decode successfully with the configured algorithm
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),  # pylint: disable=no-member
            algorithms=[settings.jwt_algorithm],
        )
        assert payload["sub"] == "test@example.com"

    def test_create_access_token_diff_data(self) -> None:
        """Test that different data produces different tokens."""
        data1 = {"sub": "user1@example.com"}
        data2 = {"sub": "user2@example.com"}
        token1 = create_access_token(data1)
        token2 = create_access_token(data2)
        assert token1 != token2

    def test_create_access_token_diff_expiry(self) -> None:
        """
        Test that same data with different expiration produces different
        tokens.
        """
        data = {"sub": "test@example.com"}
        token1 = create_access_token(data, expires_delta=timedelta(minutes=15))
        token2 = create_access_token(data, expires_delta=timedelta(minutes=30))
        # Tokens should be different due to different expiration times
        assert token1 != token2

    def test_create_access_token_with_complex_data(self) -> None:
        """Test that create_access_token handles complex data structures."""
        data = {
            "sub": "test@example.com",
            "roles": ["admin", "user"],
            "metadata": {"key": "value"},
        }
        token = create_access_token(data)

        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),  # pylint: disable=no-member
            algorithms=[settings.jwt_algorithm],
        )
        assert payload["sub"] == "test@example.com"
        assert payload["roles"] == ["admin", "user"]
        assert payload["metadata"] == {"key": "value"}

    def test_create_access_token_expired_token_fails_verification(
        self,
    ) -> None:
        """Test that an expired token fails verification."""
        data = {"sub": "test@example.com"}
        # Create token with very short expiration
        expires_delta = timedelta(seconds=-1)  # Already expired
        token = create_access_token(data, expires_delta=expires_delta)

        # Should raise exception when trying to decode expired token
        with pytest.raises(ExpiredSignatureError):
            jwt.decode(
                token,
                settings.jwt_secret_key.get_secret_value(),  # pylint: disable=no-member
                algorithms=[settings.jwt_algorithm],
            )
