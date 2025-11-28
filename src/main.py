"""Main application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import logfire
from fastapi import FastAPI
from guard.middleware import SecurityMiddleware
from guard.models import SecurityConfig
from loguru import logger

from src.admin import admin
from src.core.config import PROJECT_INFO, settings


logfire.configure(
    token=(
        settings.logfire_token.get_secret_value() if settings.logfire_token else None
    ),
)
logfire.instrument_pydantic_ai()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Lifespan context manager for FastAPI app."""
    logger.info("Starting FastAPI app...")
    yield
    logger.info("Shutting down FastAPI app...")


config = SecurityConfig(
    blocked_user_agents=["curl", "wget"],
    custom_log_file="security.log",
    rate_limit=100,
    rate_limit_window=60,
    enable_redis=True,
    redis_url=settings.redis_url.unicode_string(),
    redis_prefix="myapp:",
    custom_error_responses={
        429: "Rate limit exceeded. Please try again later.",
    },
    enable_cors=True,
    cors_allow_origins=settings.allowed_origins_list,
    cors_allow_methods=["GET", "POST"],
    cors_allow_headers=["*"],
    cors_allow_credentials=settings.environment != "development",
    passive_mode=True,
    log_suspicious_level="WARNING",
)

app = FastAPI(
    title=PROJECT_INFO["name"],
    version=PROJECT_INFO["version"],
    description=PROJECT_INFO["description"],
    lifespan=lifespan,
)

app.add_middleware(SecurityMiddleware, config=config)
admin.mount_to(app)
