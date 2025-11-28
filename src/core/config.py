"""Configuration settings for the application."""

import os
import secrets
import tomllib
from pathlib import Path
from typing import TypedDict, cast

from jwt.algorithms import get_default_algorithms
from pydantic import Field, HttpUrl, PostgresDsn, RedisDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


parent_dir = Path(__file__).resolve().parents[2]


class ProjectInfo(TypedDict):
    """Project information."""

    name: str
    version: str
    description: str


def load_project_info() -> ProjectInfo:
    """Load project metadata from pyproject.toml."""
    pyproject_path = parent_dir / "pyproject.toml"

    if not pyproject_path.exists():
        msg = f"pyproject.toml not found at {pyproject_path}"
        raise FileNotFoundError(msg)

    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    project = cast("dict", data.get("project", {}))

    project_info: ProjectInfo = {
        "name": project.get(
            "name",
            "pydantic-ai-production-ready-template",
        ),
        "version": project.get("version", "0.1.0"),
        "description": project.get(
            "description",
            "FastAPI Pydantic AI Template",
        ),
    }

    return project_info


PROJECT_INFO = load_project_info()
CURRENT_ENV = os.getenv("ENVIRONMENT", "development").lower()
env_file_path = parent_dir / f".env.{CURRENT_ENV}"


class Settings(BaseSettings):
    """Configuration settings for the application."""

    model_config = SettingsConfigDict(
        env_file=env_file_path,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: str = Field(default=CURRENT_ENV)
    logfire_token: SecretStr
    allowed_origins: str = Field(default="*")

    database_user: str
    database_password: SecretStr
    database_host: str
    database_port: int
    database_name: str

    redis_password: SecretStr
    redis_host: str = Field(default="localhost")

    jwt_secret_key: SecretStr = Field(
        default_factory=lambda: SecretStr(secrets.token_hex(32)),
    )
    jwt_algorithm: str = Field(default="HS256")

    litellm_base_url: HttpUrl = Field(default=HttpUrl("http://localhost:4000"))
    debug: bool = Field(default=False)

    access_token_expire_minutes: int = Field(default=30)

    @field_validator("jwt_algorithm", mode="before")
    @classmethod
    def validate_jwt_algorithm(cls, v: str) -> str:
        """Validate JWT algorithm."""
        if v not in get_default_algorithms():
            msg = f"Invalid JWT algorithm: {v}"
            raise ValueError(msg)
        return v

    @property
    def redis_url(self) -> RedisDsn:
        """Redis URL."""
        return RedisDsn.build(
            scheme="redis",
            password=self.redis_password.get_secret_value(),
            host=self.redis_host,
            port=6379,
        )

    @property
    def database_url(self) -> PostgresDsn:
        """Database URL."""
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.database_user,
            password=self.database_password.get_secret_value(),
            host=self.database_host,
            path=self.database_name,
        )

    @property
    def allowed_origins_list(self) -> list[str]:
        """Get allowed origins as a list."""
        origins = str(self.allowed_origins)
        if origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in origins.split(",") if o.strip()]


settings = Settings()
