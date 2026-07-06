"""Approval entity model (Q3 — separate Approval table).

One row per approval: ``requested_by``, ``approved_by``, ``status``,
``requested_at``, ``approved_at``, and context fields. Supports the
pending-approval state for lifecycle transitions (D8/D9) and ownership
transfer (D12).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, TIMESTAMP, text
from sqlalchemy.orm import Mapped, mapped_column

from kernel.db import Base


class Approval(Base):
    """Approval record — one row per approval flow (Q3, AC-19)."""

    __tablename__ = "approval"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # pending | approved | denied
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    requested_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    # Context: what is being approved (e.g. "client_lifecycle", "institution_lifecycle", "ownership_transfer")
    context_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    context_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
