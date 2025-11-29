"""Prompt service."""

import uuid
from typing import cast

from redis.asyncio import Redis
from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from src.database.database import AsyncSession
from src.models.prompt import Prompt, PromptVersion


class PromptServiceError(Exception):
    """Prompt service error."""


class PromptNotFoundError(PromptServiceError):
    """Prompt not found error."""


class PromptService:
    """Prompt service."""

    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        """Initialize the prompt service."""
        self.session = session
        self.redis = redis
        self.cache_prefix = "prompt_cache:"
        self.cache_ttl = 3600

    def _get_cache_key(self, slug: str) -> str:
        return f"{self.cache_prefix}{slug}"

    @staticmethod
    async def get_cached_content(
        session: AsyncSession,
        redis: Redis,
        slug: str,
        cache_prefix: str = "prompt_cache:",
        cache_ttl: int = 3600,
    ) -> str:
        """Get cached content for a prompt."""
        key = f"{cache_prefix}{slug}"

        cached_val = await redis.get(key)
        if cached_val:
            return cast("bytes", cached_val).decode("utf-8")

        result = await session.execute(
            select(Prompt).where(Prompt.slug == slug),
        )
        prompt = result.scalar_one_or_none()

        if prompt and prompt.content:
            await redis.set(key, prompt.content, ex=cache_ttl)
            return prompt.content

        raise PromptNotFoundError(f"Prompt not found: {slug}") from None

    async def invalidate_cache(self, slug: str) -> None:
        """Invalidate the cache for a prompt."""
        await self.redis.delete(self._get_cache_key(slug))

    async def get_all_prompts_for_admin(self) -> list[Prompt]:
        """Get all prompts for the admin."""
        result = await self.session.execute(
            select(Prompt).order_by(Prompt.slug),
        )
        return list(result.scalars().all())

    async def get_prompt_details_for_admin(
        self,
        prompt_id: str,
    ) -> Prompt | None:
        """Get full details with versions for the Editor."""
        p_uuid = uuid.UUID(prompt_id)

        stmt = (
            select(Prompt)
            .where(Prompt.id == p_uuid)
            .options(selectinload(Prompt.versions))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def save_prompt_commit(
        self,
        slug: str,
        name: str,
        content: str,
        commit_msg: str,
        prompt_id_str: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> uuid.UUID:
        """Save a prompt commit."""
        prompt_id: uuid.UUID

        if prompt_id_str:
            prompt_id = uuid.UUID(prompt_id_str)
        else:
            stmt = select(Prompt).where(Prompt.slug == slug)
            result = await self.session.execute(stmt)
            existing_prompt = result.scalar_one_or_none()

            if existing_prompt:
                prompt_id = existing_prompt.id
            else:
                new_prompt = Prompt(slug=slug, name=name, content=content)
                self.session.add(new_prompt)
                await self.session.flush()
                await self.session.refresh(new_prompt)

                new_version = PromptVersion(
                    prompt_id=new_prompt.id,
                    content=content,
                    commit_message=commit_msg,
                    is_active=True,
                    created_by_id=user_id,
                    version_number=1,
                )
                self.session.add(new_version)
                await self.session.commit()
                await self.invalidate_cache(slug)

                return new_prompt.id

        await self.session.execute(
            update(Prompt)
            .where(Prompt.id == prompt_id)
            .values(name=name, content=content, slug=slug),
        )

        max_ver_result = await self.session.execute(
            select(func.max(PromptVersion.version_number)).where(
                PromptVersion.prompt_id == prompt_id,
            ),
        )
        current_max = max_ver_result.scalar()
        next_ver = (current_max or 0) + 1

        await self.session.execute(
            update(PromptVersion)
            .where(PromptVersion.prompt_id == prompt_id)
            .values(is_active=False),
        )

        new_version = PromptVersion(
            prompt_id=prompt_id,
            content=content,
            commit_message=commit_msg,
            is_active=True,
            created_by_id=user_id,
            version_number=next_ver,
        )
        self.session.add(new_version)

        await self.session.commit()
        await self.invalidate_cache(slug)

        return prompt_id

    async def activate_version(self, version_id: str, prompt_id: str) -> bool:
        """Rollbacks/Activates a specific version."""
        v_uuid = uuid.UUID(version_id)
        p_uuid = uuid.UUID(prompt_id)

        ver_result = await self.session.execute(
            select(PromptVersion).where(PromptVersion.id == v_uuid),
        )
        target_version = ver_result.scalar_one_or_none()

        if not target_version:
            return False

        prompt_res = await self.session.execute(
            select(Prompt).where(Prompt.id == p_uuid),
        )
        prompt = prompt_res.scalar_one_or_none()

        if prompt:
            await self.session.execute(
                update(PromptVersion)
                .where(PromptVersion.prompt_id == p_uuid)
                .values(is_active=False),
            )

            target_version.is_active = True

            prompt.content = target_version.content

            self.session.add(prompt)
            self.session.add(target_version)

            await self.session.commit()
            await self.invalidate_cache(prompt.slug)
            return True

        return False
