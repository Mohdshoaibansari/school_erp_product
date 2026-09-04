"""C-05 Academic Structure — GradeAcademicYearCurriculum model.

Bridge entity that assigns a CurriculumVersion to a Grade for a specific AcademicYear.
One CurriculumVersion per Grade per AcademicYear.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class GradeAcademicYearCurriculum(Base):
    """GradeAcademicYearCurriculum entity — assigns CurriculumVersion to Grade for AcademicYear."""

    __tablename__ = "grade_academic_year_curriculum"
    __table_args__ = (
        UniqueConstraint("grade_level_id", "academic_year_id", name="uq_grade_academic_year_curriculum"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institution.id"), nullable=False)
    grade_level_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("grade_level.id"), nullable=False)
    academic_year_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic_year.id"), nullable=False)
    curriculum_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("curriculum_version.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    grade_level = relationship("GradeLevel", back_populates="grade_academic_year_curricula")
    academic_year = relationship("AcademicYear", back_populates="grade_academic_year_curricula")
    curriculum_version = relationship("CurriculumVersion", back_populates="grade_academic_year_curricula")
