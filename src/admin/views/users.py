"""Users admin view."""

from typing import Any

from pydantic import ValidationError
from starlette.requests import Request
from starlette_admin import EmailField, PasswordField, StringField
from starlette_admin.contrib.sqla import ModelView
from starlette_admin.exceptions import FormValidationError

from src.core.security import hash_password
from src.models.user import User
from src.schemas.user import UserCreate, UserUpdate


class UsersView(ModelView):
    """Users admin view."""

    exclude_fields_from_create = ["user_threads", "hashed_password"]
    exclude_fields_from_edit = ["user_threads", "hashed_password"]
    exclude_fields_from_list = ["password"]
    exclude_fields_from_detail = ["password"]

    fields = [
        "id",
        StringField(
            "name",
            label="Name",
            help_text="Enter name",
        ),
        EmailField(
            "email",
            label="Email",
            help_text="Enter email address",
        ),
        PasswordField(
            "password",
            label="Password",
            help_text="Enter new password (min 8 chars)",
        ),
        "is_deleted",
        "is_superuser",
    ]

    page_size = 5
    page_size_options = [5, 10, 25, 50]

    async def before_create(
        self,
        _request: Request,
        data: dict[str, Any],
        obj: User,
    ) -> None:
        """Validate using Pydantic Schema, then hash."""
        raw_password = data.pop("password", None)

        validation_data = {
            "name": data.get("name"),
            "email": data.get("email"),
            "password": raw_password,
        }

        try:
            validated_user = UserCreate(**validation_data)
            clean_password = validated_user.password.get_secret_value()

            if len(clean_password.encode("utf-8")) > 72:
                raise FormValidationError(
                    errors={
                        "password": "Password cannot exceed 72 bytes",
                    },
                )

            obj.hashed_password = hash_password(clean_password)

        except ValidationError as e:
            error_map = {}
            for err in e.errors():
                field_name = err["loc"][0]
                error_map[field_name] = err["msg"]
            raise FormValidationError(errors=error_map) from e

    async def before_edit(
        self,
        _request: Request,
        data: dict[str, Any],
        obj: User,
    ) -> None:
        """Validate using Pydantic Schema, then hash."""
        raw_password = data.pop("password", None)

        if raw_password:
            try:
                UserUpdate(password=raw_password)
                if len(raw_password.encode("utf-8")) > 72:
                    raise FormValidationError(
                        errors={
                            "password": "Password cannot exceed 72 bytes",
                        },
                    )

                obj.hashed_password = hash_password(raw_password)

            except ValidationError as e:
                error_map = {}
                for err in e.errors():
                    field_name = err["loc"][0]
                    if field_name == "password":
                        error_map["password"] = err["msg"]

                if error_map:
                    raise FormValidationError(error_map) from e
