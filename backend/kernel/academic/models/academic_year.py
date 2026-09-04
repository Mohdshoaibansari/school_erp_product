"""C-05 Academic Structure — AcademicYear model.

Academic cycle (e.g., "2027-28") for an institution.
Lifecycle: planning → active → closed, or planning → cancelled.
Only one active year per institution.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, String, Date, DateTime, text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class AcademicYear(Base):
    """AcademicYear entity — represents an academic cycle."""

    __tablename__ = "academic_year"
    __table_args__ = (
        UniqueConstraint("institution_id", "name", name="uq_academic_year_institution_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institution.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "2027-28"
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="planning")  # planning | active | closed | cancelled
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # actual closure timestamp for early closure
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    terms = relationship("Term", back_populates="academic_year", cascade="all, delete-orphan")
    class_academic_years = relationship("ClassAcademicYear", back_populates="academic_year", cascade="all, delete-orphan")
    grade_academic_year_curricula = relationship("GradeAcademicYearCurriculum", back_populates="academic_year")
