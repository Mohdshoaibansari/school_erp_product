"""InstitutionType entity model (D7).

JSONB template column stores the default OrgUnit tree. Configurable via API
(not hardcoded). Setup-time only — immutable on an Institution after creation.
Does NOT drive runtime module behavior (D7, AC-16).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from kernel.db import Base


class InstitutionType(Base):
    """InstitutionType entity — configurable OrgUnit template (D7)."""

    __tablename__ = "institution_type"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    # Q2: name backed by lookup table
    name_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("institution_type_name.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    is_system: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default=text("false")
    )
    # D7: JSONB nested tree of {org_unit_type, sort_order, children: [...]}
    default_org_unit_template: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )
    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"),
        onupdate=text("now()"),
    )
