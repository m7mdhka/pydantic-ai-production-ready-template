"""Prompt models."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.database.database import Base


if TYPE_CHECKING:
    from src.models.user import User


class Prompt(Base):
    """Prompt Container."""

    __tablename__ = "prompts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    content: Mapped[str | None] = mapped_column(Text, nullable=True, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    versions: Mapped[list["PromptVersion"]] = relationship(
        "PromptVersion",
        back_populates="prompt",
        cascade="all, delete-orphan",
        order_by="desc(PromptVersion.version_number)",
    )

    def __repr__(self) -> str:
        return f"<Prompt id={self.id} slug={self.slug}>"


class PromptVersion(Base):
    """Immutable history of prompt changes."""

    __tablename__ = "prompt_versions"

    __table_args__ = (
        UniqueConstraint(
            "prompt_id",
            "version_number",
            name="uq_prompt_version_number",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    prompt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    commit_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    prompt: Mapped["Prompt"] = relationship("Prompt", back_populates="versions")
    created_by: Mapped["User | None"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<PromptVersion version={self.version_number} prompt_id={self.prompt_id}>"
        )
