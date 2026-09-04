"""C-05 Academic Structure — GradeLevel model.

School-specific grade (e.g., "Grade 10"). Permanent master.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Integer, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class GradeLevel(Base):
    """GradeLevel entity — school-specific grade (Grade 1-12)."""

    __tablename__ = "grade_level"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institution.id"), nullable=False)
    org_unit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("org_unit.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Grade 10"
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    classes = relationship("Class", back_populates="grade_level", cascade="all, delete-orphan")
    curriculum = relationship("Curriculum", back_populates="grade_level", uselist=False, cascade="all, delete-orphan")
    grade_academic_year_curricula = relationship("GradeAcademicYearCurriculum", back_populates="grade_level")
