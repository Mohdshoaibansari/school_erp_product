"""C-05 Academic Structure — CurriculumVersion model.

Belongs to Curriculum. Represents a versioned snapshot of subjects.
Immutable once created (enforced at app level).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Integer, text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class CurriculumVersion(Base):
    """CurriculumVersion entity — versioned snapshot of subjects."""

    __tablename__ = "curriculum_version"
    __table_args__ = (
        UniqueConstraint("curriculum_id", "version_number", name="uq_curriculum_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institution.id"), nullable=False)
    curriculum_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("curriculum.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)  # e.g., 1, 2, 3
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "V1", "V2"
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    curriculum = relationship("Curriculum", back_populates="versions")
    subjects = relationship("Subject", back_populates="curriculum_version", cascade="all, delete-orphan")
    grade_academic_year_curricula = relationship("GradeAcademicYearCurriculum", back_populates="curriculum_version")
