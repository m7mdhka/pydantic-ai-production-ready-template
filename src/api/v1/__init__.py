from fastapi import APIRouter

from src.api.v1.auth import router as auth_router
from src.api.v1.health import health_router


v1_router = APIRouter()
v1_router.include_router(auth_router, prefix="/auth")
v1_router.include_router(health_router, prefix="/health")
