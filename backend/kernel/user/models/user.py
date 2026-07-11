"""User model (Decision 1, Decision 4, AC-4).

A user record is per-institution (Decision 1). A person who works at two
schools has two separate User accounts with two separate email addresses.
There is NO Person table.

Fields: id, client_id, institution_id, email (globally unique), name,
user_category_id (FK), lifecycle_status, created_at, updated_at.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class User(Base):
    """User table — per-institution identity."""

    __tablename__ = "app_user"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institution.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    user_category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_category.id"), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="invited")
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    user_category = relationship("UserCategory", foreign_keys=[user_category_id])
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    role_assignments = relationship("RoleAssignment", back_populates="user")
    identifiers = relationship("UserIdentifier", back_populates="user")
    lifecycle_events = relationship("UserLifecycleEvent", back_populates="user")
