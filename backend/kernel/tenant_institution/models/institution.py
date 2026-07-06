"""Institution entity model (D5 — Institution field purity and config delegation).

Carries ``client_id`` (the RLS tenant column per D1). ``institution_type_id``
is immutable after creation (D7). No tz/locale/currency/branding/academic
columns — those live in C-08/C-05 (D5, AC-17).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Integer, TIMESTAMP, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from kernel.db import Base


class Institution(Base):
    """Institution entity — belongs to a Client (D5)."""

    __tablename__ = "institution"
    __table_args__ = (
        # D5: code is within-client unique
        UniqueConstraint("client_id", "code", name="uq_institution_client_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    # D1: RLS tenant column
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("client.id"), nullable=False
    )
    # D7: immutable after creation
    institution_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("institution_type.id"), nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    primary_contact_email: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    primary_contact_phone: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    # FK → C-13 (future capability)
    address_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    # D9: lifecycle status
    current_lifecycle_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="onboarding"
    )
    established_year: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    affiliation_number: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    affiliation_board: Mapped[str | None] = mapped_column(
        String(100), nullable=True
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
