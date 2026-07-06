"""Lookup tables for configurable enums (Q2, AC-20).

These are FK-referenced by entity tables. Adding a new enum value is a data
insert, not a code change (AC-20).
"""

from __future__ import annotations

import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from kernel.db import Base


class LegalEntityType(Base):
    """Lookup table for Client ``legal_entity_type`` (Q2)."""

    __tablename__ = "legal_entity_type"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class OrgUnitType(Base):
    """Lookup table for OrgUnit ``type`` (Q2)."""

    __tablename__ = "org_unit_type"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class InstitutionTypeName(Base):
    """Lookup table for InstitutionType ``name`` (Q2)."""

    __tablename__ = "institution_type_name"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
