"""ClientUser model — client-leadership account (D1, D3e, D6a).

Client-leadership-scope users: Client Director + future Client Admins / Billing Contacts.
Stored in a separate table from app_user to enforce tier separation at the DB level.
Has a role_id column directly (per D3 — no separate client_role_assignment).
NO institution_id column — a CD manages the entire client across all institutions.

Human data lives on `person` (D6a). client_user is a thin account.

Fields: id, client_id, email, person_id (FK), role_id (FK), lifecycle_status,
created_at, updated_at.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class ClientUser(Base):
    """Client-leadership-scope user — thin account in client_user table."""

    __tablename__ = "client_user"

    id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id"), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    person_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("person.id"), nullable=True)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("role.id"), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="invited")
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    person = relationship("Person", foreign_keys=[person_id], viewonly=True)
