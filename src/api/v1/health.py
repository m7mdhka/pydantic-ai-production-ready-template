"""Health check endpoint."""

from fastapi import APIRouter

from core.config import PROJECT_INFO
from src.schemas.extras import HealthCheck

health_router = APIRouter()


@health_router.get("/")
async def health() -> HealthCheck:
    """Health check endpoint."""
    return HealthCheck(version=PROJECT_INFO["version"], status="Healthy")
