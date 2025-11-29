"""Auth service."""

from datetime import timedelta

from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.security import create_access_token, oauth2_scheme
from src.models.user import User
from src.schemas.user import Token, UserCreate, UserLogin
from src.services.user_service import (
    UserService,
    UserServiceError,
)


class AuthServiceError(Exception):
    """Exception for auth service errors."""


class InvalidCredentialsError(AuthServiceError):
    """Exception for invalid credentials errors."""


class TokenValidationError(AuthServiceError):
    """Exception for token validation errors."""


class AuthService:
    """Service for authentication operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the auth service.

        Args:
            session: The database session to use.

        """
        self.session = session
        self.user_service = UserService(session)

    async def register_user(self, user_data: UserCreate) -> User:
        """Register a new user.

        Args:
            user_data: The user data to create.

        Returns:
            The created user.

        Raises:
            UserAlreadyExistsError: If the email already exists.
            FailedToCreateUserError: If user creation fails.

        """
        try:
            return await self.user_service.create_user(user_data)
        except UserServiceError as e:
            raise e from e

    async def authenticate_user(self, user_data: UserLogin) -> User:
        """Authenticate a user with email and password.

        Args:
            user_data: The user login credentials.

        Returns:
            The authenticated user.

        Raises:
            InvalidCredentialsError: If credentials are invalid.

        """
        user = await self.user_service.verify_user_password(
            user_data.email,
            user_data.password.get_secret_value(),
        )
        if not user:
            raise InvalidCredentialsError("Incorrect email or password")
        return user

    def create_token(
        self,
        user: User,
        expires_delta: timedelta | None = None,
    ) -> Token:
        """Create an access token for a user.

        Args:
            user: The user to create a token for.
            expires_delta: Optional expiration time delta.
                If None, uses default from settings.

        Returns:
            A Token object with access_token and token_type.

        """
        if expires_delta is None:
            expires_delta = timedelta(
                minutes=settings.access_token_expire_minutes,
            )

        access_token = create_access_token(
            data={"sub": user.email},
            expires_delta=expires_delta,
        )
        return Token(
            access_token=access_token,
            token_type=oauth2_scheme.scheme_name,
        )

    async def login(self, user_data: UserLogin) -> Token:
        """Login a user and return an access token.

        Args:
            user_data: The user login credentials.

        Returns:
            A Token object with access_token and token_type.

        Raises:
            InvalidCredentialsError: If credentials are invalid.

        """
        user = await self.authenticate_user(user_data)
        return self.create_token(user)

    async def get_user_from_token(self, token: str) -> User:
        """Get a user from a JWT token.

        Args:
            token: The JWT token string.

        Returns:
            The user associated with the token.

        Raises:
            TokenValidationError: If the token is invalid or user not found.

        """
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key.get_secret_value(),
                algorithms=[settings.jwt_algorithm],
            )
            email: str = payload.get("sub")
            if email is None:
                raise TokenValidationError("Token missing subject (email)")
        except JWTError as e:
            raise TokenValidationError(f"Invalid token: {e!s}") from e

        user = await self.user_service.get_user_by_email(email)
        if user is None:
            raise TokenValidationError(f"User with email {email} not found")

        return user

    async def validate_token(self, token: str) -> tuple[bool, User | None]:
        """Validate a JWT token and return the user if valid.

        Args:
            token: The JWT token string.

        Returns:
            A tuple of (is_valid, user). user is None if token is invalid.

        """
        try:
            return True, await self.get_user_from_token(token)
        except TokenValidationError:
            return False, None
