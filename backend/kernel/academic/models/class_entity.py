"""C-05 Academic Structure — Class model.

Persistent academic group under GradeLevel. Permanent master.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Integer, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class Class(Base):
    """Class entity — persistent academic group under GradeLevel."""

    __tablename__ = "class"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institution.id"), nullable=False)
    grade_level_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("grade_level.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "11"
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    grade_level = relationship("GradeLevel", back_populates="classes")
    class_academic_years = relationship("ClassAcademicYear", back_populates="class_entity", cascade="all, delete-orphan")
