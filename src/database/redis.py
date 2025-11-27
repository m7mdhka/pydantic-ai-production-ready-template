"""Redis utilities."""

from redis import asyncio
from redis.asyncio.client import Redis

from src.core.config import settings


async def get_redis_pool() -> Redis:
    """Get Redis pool."""
    return asyncio.from_url(
        settings.redis_url.unicode_string(),
        encoding="utf-8",
        decode_responses=True,
    )
