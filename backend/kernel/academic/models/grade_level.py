"""C-05 Academic Structure — GradeLevel model (D2, D15).

School-specific grade (e.g., "Grade 10"). Year-specific.
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
    academic_year_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic_year.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Grade 10"
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    academic_year = relationship("AcademicYear", back_populates="grade_levels")
    classes = relationship("ClassEntity", back_populates="grade_level", cascade="all, delete-orphan")
