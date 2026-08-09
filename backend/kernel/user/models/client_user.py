"""ClientUser model (D1, D3, D10).

Client-leadership-scope users: Client Director + future Client Admins / Billing Contacts.
Stored in a separate table from app_user to enforce tier separation at the DB level.
Has a role_id column directly (per D3 — no separate client_role_assignment).
NO institution_id column — a CD manages the entire client across all institutions.

Fields: id, client_id, email, name, user_category_id (FK), role_id (FK), lifecycle_status,
created_at, updated_at. Mirrors app_user columns but adds role_id and removes institution_id.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column

from kernel.db import Base


class ClientUser(Base):
    """Client-leadership-scope user — stored in client_user table."""

    __tablename__ = "client_user"

    id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id"), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    user_category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_category.id"), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("role.id"), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="invited")
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
