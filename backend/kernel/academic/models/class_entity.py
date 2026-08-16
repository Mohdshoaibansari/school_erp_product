"""C-05 Academic Structure — Class model (D2, D15).

Grade section grouping (e.g., "10A"). Year-specific.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Integer, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class ClassEntity(Base):
    """Class entity — grade section grouping (10A, 10B)."""

    __tablename__ = "class"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institution.id"), nullable=False)
    academic_year_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic_year.id"), nullable=False)
    grade_level_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("grade_level.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "10A"
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    academic_year = relationship("AcademicYear", back_populates="classes")
    grade_level = relationship("GradeLevel", back_populates="classes")
    sections = relationship("Section", back_populates="class_entity", cascade="all, delete-orphan")
