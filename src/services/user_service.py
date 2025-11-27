"""User service."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import hash_password, verify_password
from src.models.user import User
from src.schemas.user import UserCreate, UserUpdate


class UserServiceError(Exception):
    """Exception for user service errors."""


class UserAlreadyExistsError(UserServiceError):
    """Exception for user already exists errors."""


class FailedToCreateUserError(UserServiceError):
    """Exception for failed to create user errors."""


class UserNotFoundError(UserServiceError):
    """Exception for user not found errors."""


class FailedToUpdateUserError(UserServiceError):
    """Exception for failed to update user errors."""


class UserAlreadyDeletedError(UserServiceError):
    """Exception for user already deleted errors."""


class UserService:
    """Service for user operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the user service.

        Args:
            session: The database session to use.

        """
        self.session = session

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user.

        Args:
            user_data: The user data to create.

        Returns:
            The created user.

        Raises:
            ValueError: If the email already exists.

        """
        existing_user = await self.get_user_by_email(user_data.email)
        if existing_user:
            msg = f"User with email {user_data.email} already exists"
            raise UserAlreadyExistsError(msg)

        hashed_password = hash_password(user_data.password)

        user = User(
            name=user_data.name,
            email=user_data.email,
            hashed_password=hashed_password,
        )

        try:
            self.session.add(user)
            await self.session.flush()
            await self.session.refresh(user)
        except IntegrityError as e:
            await self.session.rollback()
            msg = f"Failed to create user: {e!s}"
            raise FailedToCreateUserError(msg) from e

        return user

    async def get_user_by_id(
        self,
        user_id: uuid.UUID,
    ) -> User | None:
        """Get a user by ID.

        Args:
            user_id: The user ID to search for.

        Returns:
            The user if found, None otherwise.

        """
        query = select(User).where(User.id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_by_email(
        self,
        email: str,
    ) -> User | None:
        """Get a user by email.

        Args:
            email: The email to search for.
            include_deleted: Whether to include soft-deleted users.

        Returns:
            The user if found, None otherwise.

        """
        query = select(User).where(User.email == email)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_user(
        self,
        user_id: uuid.UUID,
        user_data: UserUpdate,
    ) -> User:
        """Update a user.

        Args:
            user_id: The ID of the user to update.
            user_data: The updated user data.

        Returns:
            The updated user.

        Raises:
            ValueError: If the user is not found or email already exists.

        """
        user = await self.get_user_by_id(user_id)
        if not user:
            msg = f"User with ID {user_id} not found"
            raise UserNotFoundError(msg)

        if user_data.email and user_data.email != user.email:
            existing_user = await self.get_user_by_email(user_data.email)
            if existing_user:
                msg = f"User with email {user_data.email} already exists"
                raise UserAlreadyExistsError(msg)

        if user_data.name is not None:
            user.name = user_data.name
        if user_data.email is not None:
            user.email = user_data.email
        if user_data.password is not None:
            user.hashed_password = hash_password(user_data.password)
        if user_data.is_superuser is not None:
            user.is_superuser = user_data.is_superuser

        user.updated_at = datetime.now(UTC)

        try:
            await self.session.flush()
            await self.session.refresh(user)
        except IntegrityError as e:
            await self.session.rollback()
            msg = f"Failed to update user: {e!s}"
            raise FailedToUpdateUserError(msg) from e

        return user

    async def delete_user(
        self,
        user_id: uuid.UUID,
        *,
        hard_delete: bool = False,
    ) -> bool:
        """Delete a user (soft delete by default).

        Args:
            user_id: The ID of the user to delete.
            hard_delete: If True, permanently delete the user.
                If False, soft delete.

        Returns:
            True if the user was deleted, False if not found.

        Raises:
            ValueError: If the user is not found.

        """
        user = await self.get_user_by_id(user_id)
        if not user:
            msg = f"User with ID {user_id} not found"
            raise UserNotFoundError(msg)

        if not hard_delete and user.is_deleted:
            msg = f"User with ID {user_id} is already deleted"
            raise UserAlreadyDeletedError(msg)

        if hard_delete:
            await self.session.delete(user)
        else:
            user.is_deleted = True
            user.deleted_at = datetime.now(UTC)

        await self.session.flush()
        return True

    async def list_users(
        self,
        *,
        page: int = 1,
        page_size: int = 10,
        include_deleted: bool = False,
    ) -> tuple[list[User], int]:
        """List users with pagination.

        Args:
            page: The page number (1-indexed).
            page_size: The number of items per page.
            include_deleted: Whether to include soft-deleted users.

        Returns:
            A tuple of (list of users, total count).

        """
        query = select(User)
        count_query = select(User).with_only_columns(User.id)

        if not include_deleted:
            query = query.where(~User.is_deleted)
            count_query = count_query.where(~User.is_deleted)

        count_result = await self.session.execute(count_query)
        total = len(count_result.scalars().all())

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(User.created_at.desc())

        result = await self.session.execute(query)
        users = list(result.scalars().all())

        return users, total

    async def verify_user_password(
        self,
        email: str,
        password: str,
    ) -> User | None:
        """Verify a user's password.

        Args:
            email: The user's email.
            password: The plain text password to verify.

        Returns:
            The user if password is correct, None otherwise.

        """
        user = await self.get_user_by_email(email)
        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        return user

    async def user_exists(self, email: str) -> bool:
        """Check if a user with the given email exists.

        Args:
            email: The email to check.

        Returns:
            True if the user exists, False otherwise.

        """
        user = await self.get_user_by_email(email)
        return user is not None
