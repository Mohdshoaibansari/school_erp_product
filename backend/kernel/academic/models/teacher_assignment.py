"""C-05 Academic Structure — TeacherAssignment model (D11).

Links a teacher to a subject within a section for an academic year.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class TeacherAssignment(Base):
    """TeacherAssignment entity — teacher → section + subject + academic year."""

    __tablename__ = "teacher_assignment"
    __table_args__ = (
        UniqueConstraint("teacher_id", "section_id", "subject_id", name="uq_teacher_assignment"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institution.id"), nullable=False)
    academic_year_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic_year.id"), nullable=False)
    teacher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    section_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("section.id"), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subject.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active")  # active | inactive
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    academic_year = relationship("AcademicYear", back_populates="teacher_assignments")
    teacher = relationship("User", foreign_keys=[teacher_id])
    section = relationship("Section", back_populates="teacher_assignments")
    subject = relationship("Subject", back_populates="teacher_assignments")
