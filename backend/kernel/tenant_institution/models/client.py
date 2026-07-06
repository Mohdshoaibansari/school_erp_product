"""Client entity model (D4 — Client field purity and config delegation).

The Client IS the tenant — it has no ``client_id`` column (Q1).
Its RLS policy is self-visible: ``id = current_client_id`` (Q1, AC-14).

Field purity (D4, AC-17): no timezone/locale/currency/branding/subscription/
billing columns — those live in C-08/C-07/C-23 respectively.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, TIMESTAMP, text
from sqlalchemy.orm import Mapped, mapped_column

from kernel.db import Base


class Client(Base):
    """Client entity — the tenant root (D4)."""

    __tablename__ = "client"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    # D3: slug immutable, globally unique
    slug: Mapped[str] = mapped_column(
        String(63), unique=True, nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Q2: configurable enum via lookup table FK
    legal_entity_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("legal_entity_type.id"), nullable=False
    )
    tax_registration_number: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    primary_contact_email: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    primary_contact_phone: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    billing_contact_email: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    # FK → C-13 (Address). C-13 is a future capability; the FK constraint
    # will be added when C-13's table exists. For now it's a plain UUID column.
    address_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True
    )
    # D8: lifecycle status
    current_lifecycle_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="prospective"
    )
    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"),
        onupdate=text("now()"),
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
