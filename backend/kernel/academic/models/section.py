"""C-05 Academic Structure — Section model (D8, D10, D15).

Home-room unit (e.g., "Section A of Class 10A").
Year-specific. Has homeroom_teacher_id.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Integer, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class Section(Base):
    """Section entity — home-room unit with homeroom teacher."""

    __tablename__ = "section"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institution.id"), nullable=False)
    academic_year_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic_year.id"), nullable=False)
    class_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("class.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "A"
    homeroom_teacher_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    academic_year = relationship("AcademicYear", back_populates="sections")
    class_entity = relationship("ClassEntity", back_populates="sections")
    homeroom_teacher = relationship("User", foreign_keys=[homeroom_teacher_id])
    enrollments = relationship("StudentEnrollment", back_populates="section")
    teacher_assignments = relationship("TeacherAssignment", back_populates="section")
