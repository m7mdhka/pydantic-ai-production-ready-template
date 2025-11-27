import uuid
from datetime import datetime

import pytest
from pydantic import SecretStr, ValidationError

from src.schemas import (Token, UserCreate, UserListResponse, UserLogin,
                         UserResponse, UserUpdate)


def test_password_valid():
    """Test that a valid password (length >= 8 + digit) passes."""
    password = "SecurePassword1"
    user = UserCreate(name="Test", email="test@example.com", password=password)
    assert user.password.get_secret_value() == password


def test_password_too_short():
    """Test that passwords shorter than MIN_PASSWORD_LENGTH fail."""
    short_pw = "Pass1"  # 5 chars
    with pytest.raises(ValidationError) as exc:
        UserCreate(name="Test", email="test@example.com", password=short_pw)

    errors = exc.value.errors()
    assert any(
        "min_length" in e["type"] or "Password is too short" in e["msg"] for e in errors
    )


def test_password_no_digit():
    """Test that a password without a number fails the custom validator."""
    no_digit_pw = "PasswordWithoutNumber"
    with pytest.raises(ValidationError) as exc:
        UserCreate(name="Test", email="test@example.com", password=no_digit_pw)

    assert "Password must contain a number" in str(exc.value)


def test_password_is_secret():
    """Ensure password is hidden in string representation."""
    user = UserCreate(name="Test", email="test@example.com", password="Password1")
    assert str(user.password) == "**********"
    assert repr(user.password) == "SecretStr('**********')"
    assert user.password.get_secret_value() == "Password1"


def test_user_create_email_normalization():
    """Test that EmailStr accepts valid emails and (usually) normalizes them."""
    user = UserCreate(name="Test", email="TEST@Example.com", password="Password1")
    assert user.email == "TEST@example.com"


def test_user_create_invalid_email():
    with pytest.raises(ValidationError) as exc:
        UserCreate(name="Test", email="not-an-email", password="Password1")
    assert "value is not a valid email address" in str(exc.value)


def test_user_create_empty_name():
    with pytest.raises(ValidationError):
        UserCreate(name="", email="test@example.com", password="Password1")


def test_user_update_all_fields():
    """Test updating all fields works."""
    update = UserUpdate(
        name="New Name",
        email="new@example.com",
        password="NewPassword1",
        is_superuser=True,
    )
    assert update.name == "New Name"
    assert update.password.get_secret_value() == "NewPassword1"
    assert update.is_superuser is True


def test_user_update_partial():
    """Test updating only one field allows others to be None."""
    update = UserUpdate(name="Just Name")
    assert update.name == "Just Name"
    assert update.email is None
    assert update.password is None


def test_user_update_password_validation():
    """Test that the custom password validator still runs on Update schemas."""
    with pytest.raises(ValidationError) as exc:
        UserUpdate(password="NoDigit")
    assert "Password must contain a number" in str(exc.value)


def test_user_response_serialization():
    """Test standard instantiation."""
    uid = uuid.uuid4()
    now = datetime.now()

    resp = UserResponse(
        id=uid,
        name="Test",
        email="test@example.com",
        created_at=now,
        is_superuser=False,
    )
    assert resp.id == uid
    assert resp.created_at == now


def test_user_response_from_attributes():
    """Test 'from_attributes=True' (ORM mode equivalent)."""

    class MockORMUser:
        def __init__(self):
            self.id = uuid.uuid4()
            self.name = "ORM User"
            self.email = "orm@example.com"
            self.created_at = datetime.now()
            self.updated_at = None
            self.is_superuser = True
            # extra fields should be ignored
            self.hashed_password = "hash"

    orm_obj = MockORMUser()
    resp = UserResponse.model_validate(orm_obj)

    assert resp.name == "ORM User"
    assert resp.is_superuser is True
    assert resp.id == orm_obj.id


def test_user_list_response():
    uid = uuid.uuid4()
    now = datetime.now()
    user_resp = UserResponse(
        id=uid,
        name="A",
        email="a@a.com",
        created_at=now,
        is_superuser=False,
    )

    lst = UserListResponse(
        users=[user_resp],
        total=100,
        page=1,
        page_size=10,
        total_pages=10,
    )
    assert len(lst.users) == 1
    assert lst.total == 100


def test_user_login():
    login = UserLogin(email="test@test.com", password="Password1")
    assert isinstance(login.password, SecretStr)
    assert login.password.get_secret_value() == "Password1"


def test_token_schema():
    token = Token(access_token="abc", token_type="bearer")
    assert token.access_token == "abc"
