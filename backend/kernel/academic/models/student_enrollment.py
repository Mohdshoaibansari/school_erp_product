"""C-05 Academic Structure — StudentEnrollment model (D12).

Links a student to a section for an academic year.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, DateTime, text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class StudentEnrollment(Base):
    """StudentEnrollment entity — student → section + academic year."""

    __tablename__ = "student_enrollment"
    __table_args__ = (
        UniqueConstraint("student_id", "academic_year_id", name="uq_student_enrollment_year"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institution.id"), nullable=False)
    academic_year_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic_year.id"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    section_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("section.id"), nullable=False)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active")  # active | transferred | withdrawn
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    academic_year = relationship("AcademicYear", back_populates="enrollments")
    student = relationship("User", foreign_keys=[student_id])
    section = relationship("Section", back_populates="enrollments")
