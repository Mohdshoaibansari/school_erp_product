"""OrgUnit entity model (D6 — adjacency list + recursive CTE hierarchy).

Carries ``client_id`` (RLS) and ``institution_id`` (default repo filter, NOT in
RLS per D1). ``type`` is immutable after creation. Archive-only (no hard delete).
Cycle prevention is app-side (Q6 — NO DB trigger).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Integer, TIMESTAMP, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from kernel.db import Base


class OrgUnit(Base):
    """OrgUnit entity — structural/administrative container (D6).

    Pure structure: no academic metadata (D10, AC-18). ``homeroom_teacher_id``
    is NOT on this table (belongs to C-05 or C-02).
    """

    __tablename__ = "org_unit"
    __table_args__ = (
        # D6: code within-institution unique
        UniqueConstraint("institution_id", "code", name="uq_org_unit_institution_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    # D1: RLS tenant column
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("client.id"), nullable=False
    )
    # D1: default repo filter (NOT in RLS)
    institution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("institution.id"), nullable=False
    )
    # D6: adjacency list — nullable = root
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("org_unit.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Q2: configurable enum via lookup table; immutable after creation (D6)
    type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("org_unit_type.id"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # D6: lifecycle status — active / inactive / archived
    current_lifecycle_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
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
