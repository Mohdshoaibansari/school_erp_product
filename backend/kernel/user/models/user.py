"""User model — per-institution account (D1, D3b, D6a).

A user record is per-institution (D3b). Human data lives on `person` (D6a).
The User table (app_user) is a thin account: auth/tenant fields + person_id FK.

Fields: id, client_id, institution_id, email, person_id (FK), lifecycle_status,
created_at, updated_at.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class User(Base):
    """User table — per-institution identity (thin account)."""

    __tablename__ = "app_user"

    id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id"), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    institution_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("institution.id"), nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    person_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("person.id"), nullable=True)
    lifecycle_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="invited")
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    person = relationship("Person", foreign_keys=[person_id], viewonly=True)
    role_assignments = relationship("RoleAssignment",
        primaryjoin="User.id == foreign(RoleAssignment.user_id)",
        viewonly=True,
    )
    identifiers = relationship("UserIdentifier", back_populates="user")
    lifecycle_events = relationship("UserLifecycleEvent", back_populates="user")
