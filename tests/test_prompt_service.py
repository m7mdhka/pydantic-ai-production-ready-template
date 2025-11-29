"""Tests for prompt service."""

import uuid
from typing import cast
from unittest.mock import AsyncMock

import pytest
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.prompt import Prompt, PromptVersion
from src.services.prompt_service import (
    PromptNotFoundError,
    PromptService,
)

# pylint: disable=redefined-outer-name


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Create a mock Redis client."""
    redis = AsyncMock(spec=Redis)
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    return redis


@pytest.mark.asyncio
async def test_get_cached_content_from_cache(
    db_session: AsyncSession,
    mock_redis: AsyncMock,
) -> None:
    """Test getting cached content from Redis cache."""
    cached_content = "Cached prompt content"
    mock_redis.get.return_value = cached_content.encode("utf-8")

    content = await PromptService.get_cached_content(
        db_session,
        cast(Redis, mock_redis),
        "test-slug",
    )

    assert content == cached_content
    mock_redis.get.assert_called_once_with("prompt_cache:test-slug")
    mock_redis.set.assert_not_called()


@pytest.mark.asyncio
async def test_get_cached_content_from_database(
    db_session: AsyncSession,
    mock_redis: AsyncMock,
) -> None:
    """Test getting content from database when not in cache."""
    # Create a prompt in the database
    prompt = Prompt(
        slug="test-slug",
        name="Test Prompt",
        content="Database prompt content",
    )
    db_session.add(prompt)
    await db_session.commit()

    # Mock Redis to return None (cache miss)
    mock_redis.get.return_value = None

    content = await PromptService.get_cached_content(
        db_session,
        cast(Redis, mock_redis),
        "test-slug",
    )

    assert content == "Database prompt content"
    mock_redis.get.assert_called_once_with("prompt_cache:test-slug")
    mock_redis.set.assert_called_once_with(
        "prompt_cache:test-slug",
        "Database prompt content",
        ex=3600,
    )


@pytest.mark.asyncio
async def test_get_cached_content_not_found(
    db_session: AsyncSession,
    mock_redis: AsyncMock,
) -> None:
    """Test getting content when prompt doesn't exist."""
    mock_redis.get.return_value = None

    with pytest.raises(
        PromptNotFoundError,
        match="Prompt not found: nonexistent",
    ):
        await PromptService.get_cached_content(
            db_session,
            cast(Redis, mock_redis),
            "nonexistent",
        )


@pytest.mark.asyncio
async def test_get_cached_content_custom_prefix_and_ttl(
    db_session: AsyncSession,
    mock_redis: AsyncMock,
) -> None:
    """Test getting cached content with custom prefix and TTL."""
    prompt = Prompt(
        slug="test-slug",
        name="Test Prompt",
        content="Test content",
    )
    db_session.add(prompt)
    await db_session.commit()

    mock_redis.get.return_value = None

    await PromptService.get_cached_content(
        db_session,
        cast(Redis, mock_redis),
        "test-slug",
        cache_prefix="custom:",
        cache_ttl=7200,
    )

    mock_redis.set.assert_called_once_with(
        "custom:test-slug",
        "Test content",
        ex=7200,
    )


@pytest.mark.asyncio
async def test_invalidate_cache(
    db_session: AsyncSession,
    mock_redis: AsyncMock,
) -> None:
    """Test invalidating cache for a prompt."""
    service = PromptService(db_session, cast(Redis, mock_redis))

    await service.invalidate_cache("test-slug")

    mock_redis.delete.assert_called_once_with("prompt_cache:test-slug")


@pytest.mark.asyncio
async def test_get_all_prompts_for_admin(
    db_session: AsyncSession,
    mock_redis: AsyncMock,
) -> None:
    """Test getting all prompts for admin."""
    # Create multiple prompts
    prompt1 = Prompt(slug="b-prompt", name="B Prompt", content="Content B")
    prompt2 = Prompt(slug="a-prompt", name="A Prompt", content="Content A")
    prompt3 = Prompt(slug="c-prompt", name="C Prompt", content="Content C")
    db_session.add_all([prompt1, prompt2, prompt3])
    await db_session.commit()

    service = PromptService(db_session, cast(Redis, mock_redis))
    prompts = await service.get_all_prompts_for_admin()

    assert len(prompts) == 3
    # Should be ordered by slug
    assert prompts[0].slug == "a-prompt"
    assert prompts[1].slug == "b-prompt"
    assert prompts[2].slug == "c-prompt"


@pytest.mark.asyncio
async def test_get_all_prompts_for_admin_empty(
    db_session: AsyncSession,
    mock_redis: AsyncMock,
) -> None:
    """Test getting all prompts when none exist."""
    service = PromptService(db_session, cast(Redis, mock_redis))
    prompts = await service.get_all_prompts_for_admin()

    assert prompts == []


@pytest.mark.asyncio
async def test_get_prompt_details_for_admin(
    db_session: AsyncSession,
    mock_redis: AsyncMock,
) -> None:
    """Test getting prompt details with versions."""
    prompt = Prompt(slug="test-slug", name="Test Prompt", content="Content")
    db_session.add(prompt)
    await db_session.flush()

    version1 = PromptVersion(
        prompt_id=prompt.id,
        version_number=1,
        content="Version 1",
        commit_message="Initial version",
        is_active=True,
    )
    version2 = PromptVersion(
        prompt_id=prompt.id,
        version_number=2,
        content="Version 2",
        commit_message="Updated version",
        is_active=False,
    )
    db_session.add_all([version1, version2])
    await db_session.commit()

    service = PromptService(db_session, cast(Redis, mock_redis))
    result = await service.get_prompt_details_for_admin(str(prompt.id))

    assert result is not None
    assert result.id == prompt.id
    assert result.slug == "test-slug"
    assert len(result.versions) == 2


@pytest.mark.asyncio
async def test_get_prompt_details_for_admin_not_found(
    db_session: AsyncSession,
    mock_redis: AsyncMock,
) -> None:
    """Test getting prompt details when prompt doesn't exist."""
    service = PromptService(db_session, cast(Redis, mock_redis))
    fake_id = str(uuid.uuid4())

    result = await service.get_prompt_details_for_admin(fake_id)

    assert result is None


@pytest.mark.asyncio
async def test_save_prompt_commit_new_prompt(
    db_session: AsyncSession,
    mock_redis: AsyncMock,
) -> None:
    """Test saving a new prompt commit."""
    service = PromptService(db_session, cast(Redis, mock_redis))

    prompt_id = await service.save_prompt_commit(
        slug="new-slug",
        name="New Prompt",
        content="New content",
        commit_msg="Initial commit",
    )

    assert prompt_id is not None

    # Verify prompt was created
    prompt = await db_session.get(Prompt, prompt_id)
    assert prompt is not None
    assert prompt.slug == "new-slug"
    assert prompt.name == "New Prompt"
    assert prompt.content == "New content"

    # Verify version was created
    versions = await db_session.execute(
        select(PromptVersion).where(PromptVersion.prompt_id == prompt_id),
    )
    version_list = list(versions.scalars().all())
    assert len(version_list) == 1
    assert version_list[0].version_number == 1
    assert version_list[0].is_active is True
    assert version_list[0].content == "New content"
    assert version_list[0].commit_message == "Initial commit"

    # Verify cache was invalidated
    mock_redis.delete.assert_called_once_with("prompt_cache:new-slug")


@pytest.mark.asyncio
async def test_save_prompt_commit_update_existing(
    db_session: AsyncSession,
    mock_redis: AsyncMock,
) -> None:
    """Test updating an existing prompt with new version."""
    # Create existing prompt with version
    prompt = Prompt(
        slug="existing-slug",
        name="Existing",
        content="Old content",
    )
    db_session.add(prompt)
    await db_session.flush()

    version1 = PromptVersion(
        prompt_id=prompt.id,
        version_number=1,
        content="Old content",
        commit_message="Initial",
        is_active=True,
    )
    db_session.add(version1)
    await db_session.commit()

    service = PromptService(db_session, cast(Redis, mock_redis))

    prompt_id = await service.save_prompt_commit(
        slug="existing-slug",
        name="Updated Name",
        content="New content",
        commit_msg="Updated commit",
        prompt_id_str=str(prompt.id),
    )

    assert prompt_id == prompt.id

    # Verify prompt was updated
    await db_session.refresh(prompt)
    assert prompt.name == "Updated Name"
    assert prompt.content == "New content"

    # Verify new version was created and old one deactivated
    versions = await db_session.execute(
        select(PromptVersion)
        .where(PromptVersion.prompt_id == prompt.id)
        .order_by(PromptVersion.version_number),
    )
    version_list = list(versions.scalars().all())
    assert len(version_list) == 2
    assert version_list[0].version_number == 1
    assert version_list[0].is_active is False
    assert version_list[1].version_number == 2
    assert version_list[1].is_active is True
    assert version_list[1].content == "New content"
    assert version_list[1].commit_message == "Updated commit"


@pytest.mark.asyncio
async def test_save_prompt_commit_by_slug(
    db_session: AsyncSession,
    mock_redis: AsyncMock,
) -> None:
    """Test saving prompt commit by slug when prompt_id_str is None."""
    # Create existing prompt
    prompt = Prompt(slug="slug-prompt", name="Slug Prompt", content="Content")
    db_session.add(prompt)
    await db_session.commit()

    service = PromptService(db_session, cast(Redis, mock_redis))

    prompt_id = await service.save_prompt_commit(
        slug="slug-prompt",
        name="Updated",
        content="New content",
        commit_msg="Update",
    )

    assert prompt_id == prompt.id
    mock_redis.delete.assert_called_once_with("prompt_cache:slug-prompt")


@pytest.mark.asyncio
async def test_save_prompt_commit_with_user_id(
    db_session: AsyncSession,
    mock_redis: AsyncMock,
) -> None:
    """Test saving prompt commit with user_id."""
    user_id = uuid.uuid4()
    service = PromptService(db_session, cast(Redis, mock_redis))

    prompt_id = await service.save_prompt_commit(
        slug="user-prompt",
        name="User Prompt",
        content="Content",
        commit_msg="Commit",
        user_id=user_id,
    )

    versions = await db_session.execute(
        select(PromptVersion).where(PromptVersion.prompt_id == prompt_id),
    )
    version = versions.scalar_one()
    assert version.created_by_id == user_id


@pytest.mark.asyncio
async def test_activate_version_success(
    db_session: AsyncSession,
    mock_redis: AsyncMock,
) -> None:
    """Test successfully activating a version."""
    # Create prompt with multiple versions
    prompt = Prompt(
        slug="version-prompt",
        name="Version Prompt",
        content="Current",
    )
    db_session.add(prompt)
    await db_session.flush()

    version1 = PromptVersion(
        prompt_id=prompt.id,
        version_number=1,
        content="Version 1",
        is_active=True,
    )
    version2 = PromptVersion(
        prompt_id=prompt.id,
        version_number=2,
        content="Version 2",
        is_active=False,
    )
    db_session.add_all([version1, version2])
    await db_session.commit()

    service = PromptService(db_session, cast(Redis, mock_redis))

    result = await service.activate_version(
        str(version1.id),
        str(prompt.id),
    )

    assert result is True

    # Verify version1 is now active
    await db_session.refresh(version1)
    assert version1.is_active is True

    # Verify prompt content was updated
    await db_session.refresh(prompt)
    assert prompt.content == "Version 1"

    # Verify cache was invalidated
    mock_redis.delete.assert_called_once_with("prompt_cache:version-prompt")


@pytest.mark.asyncio
async def test_activate_version_not_found(
    db_session: AsyncSession,
    mock_redis: AsyncMock,
) -> None:
    """Test activating a version that doesn't exist."""
    prompt = Prompt(slug="test", name="Test", content="Content")
    db_session.add(prompt)
    await db_session.commit()

    service = PromptService(db_session, cast(Redis, mock_redis))

    fake_version_id = str(uuid.uuid4())
    result = await service.activate_version(fake_version_id, str(prompt.id))

    assert result is False


@pytest.mark.asyncio
async def test_activate_version_prompt_not_found(
    db_session: AsyncSession,
    mock_redis: AsyncMock,
) -> None:
    """Test activating a version when prompt doesn't exist."""
    version = PromptVersion(
        prompt_id=uuid.uuid4(),
        version_number=1,
        content="Content",
        is_active=False,
    )
    db_session.add(version)
    await db_session.commit()

    service = PromptService(db_session, cast(Redis, mock_redis))

    fake_prompt_id = str(uuid.uuid4())
    result = await service.activate_version(str(version.id), fake_prompt_id)

    assert result is False


@pytest.mark.asyncio
async def test_get_cache_key(
    db_session: AsyncSession,
    mock_redis: AsyncMock,
) -> None:
    """Test internal cache key generation."""
    service = PromptService(db_session, cast(Redis, mock_redis))

    # pylint: disable=protected-access
    key = service._get_cache_key("test-slug")

    assert key == "prompt_cache:test-slug"


@pytest.mark.asyncio
async def test_get_cached_content_prompt_without_content(
    db_session: AsyncSession,
    mock_redis: AsyncMock,
) -> None:
    """Test getting cached content when prompt has no content."""
    prompt = Prompt(slug="empty-prompt", name="Empty", content=None)
    db_session.add(prompt)
    await db_session.commit()

    mock_redis.get.return_value = None

    with pytest.raises(PromptNotFoundError):
        await PromptService.get_cached_content(
            db_session,
            cast(Redis, mock_redis),
            "empty-prompt",
        )
