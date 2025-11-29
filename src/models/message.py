"""Message model with role enum."""

import uuid
from enum import Enum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.database.database import Base


class MessageRole(str, Enum):
    """Enum for message sender roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(Base):
    """Message model."""

    __tablename__ = "messages"
    __table_args__ = (
        Index(
            "ix_message_thread_seq",
            "thread_id",
            "sequence_num",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sequence_num: Mapped[int] = mapped_column(Integer, nullable=False)

    content: Mapped[str] = mapped_column(Text, nullable=False)

    role: Mapped[MessageRole] = mapped_column(
        SQLEnum(MessageRole, name="message_role"),
        nullable=False,
        default=MessageRole.USER,
    )

    parts: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )

    extra_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
        server_default=text("'{}'::jsonb"),
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    thread = relationship("Thread", back_populates="messages")

    def __repr__(self) -> str:
        """Return a string representation of the message."""
        return f"<Message id={self.id} thread_id={self.thread_id} role={self.role}>"
