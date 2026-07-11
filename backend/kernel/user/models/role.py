"""Role lookup model (Decision 10, R6).

Configurable lookup table for roles. Default seed data:
Teacher, HOD, Principal, Student, Parent, Staff, Admin. Adding a new role
is a data insert, not a code change.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Mapped, mapped_column

from kernel.db import Base


class Role(Base):
    """Role lookup table."""

    __tablename__ = "role"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
