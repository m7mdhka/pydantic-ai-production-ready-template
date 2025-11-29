"""User model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.database.database import Base


class User(Base):
    """User model."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        default="",
    )
    hashed_password: Mapped[str] = mapped_column(String, nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
        nullable=False,
        index=True,
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
        nullable=False,
    )

    user_threads = relationship(
        "Thread",
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """Return a string representation of the user."""
        return f"<User id={self.id} email={self.email}>"
