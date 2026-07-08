"""Lifecycle event and ownership transfer tables (D8, D9, D12, Q3).

- ``client_lifecycle_events`` — Client lifecycle history (D8)
- ``institution_lifecycle_events`` — Institution lifecycle history (D9)
- ``ownership_transfer_events`` — Institution ownership transfer records (D12)

All carry ``client_id`` for RLS (D1). FK to ``Approval`` where applicable (Q3).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, TIMESTAMP, text
from sqlalchemy.orm import Mapped, mapped_column

from kernel.db import Base


class ClientLifecycleEvent(Base):
    """Client lifecycle history — one row per transition (D8)."""

    __tablename__ = "client_lifecycle_event"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    # D1: RLS tenant column (same as client id — the event belongs to that client)
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("client.id"), nullable=False
    )
    # D8: state entered
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    entered_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    # Q3: FK to Approval if applicable
    approval_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("approval.id"), nullable=True
    )


class InstitutionLifecycleEvent(Base):
    """Institution lifecycle history — one row per transition (D9)."""

    __tablename__ = "institution_lifecycle_event"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    # D1: RLS tenant column
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("client.id"), nullable=False
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("institution.id"), nullable=False
    )
    # D9: state entered
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    entered_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    # Q3: FK to Approval if applicable
    approval_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("approval.id"), nullable=True
    )


class OwnershipTransferEvent(Base):
    """Ownership transfer record — full operational transfer (D12, AC-11).

    Captures: from_client, to_client, institution, approved_by, consent_source,
    consent_dest, transferred_at, reason.
    """

    __tablename__ = "ownership_transfer_event"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    # D1: RLS tenant column — the new owner (to_client) after transfer
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("client.id"), nullable=False
    )
    from_client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("client.id"), nullable=False
    )
    to_client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("client.id"), nullable=False
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("institution.id"), nullable=False
    )
    approved_by: Mapped[str] = mapped_column(String(255), nullable=False)
    consent_source: Mapped[bool] = mapped_column(nullable=False, default=False)
    consent_dest: Mapped[bool] = mapped_column(nullable=False, default=False)
    transferred_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Q3: FK to Approval
    approval_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("approval.id"), nullable=True
    )
