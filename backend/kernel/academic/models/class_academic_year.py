"""C-05 Academic Structure — ClassAcademicYear model.

First-class business entity representing the year-specific offering/configuration of a permanent Class.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Boolean, text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class ClassAcademicYear(Base):
    """ClassAcademicYear entity — year-specific offering of a permanent Class."""

    __tablename__ = "class_academic_year"
    __table_args__ = (
        UniqueConstraint("class_id", "academic_year_id", name="uq_class_academic_year"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institution.id"), nullable=False)
    class_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("class.id"), nullable=False)
    academic_year_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic_year.id"), nullable=False)
    offered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    class_entity = relationship("Class", back_populates="class_academic_years")
    academic_year = relationship("AcademicYear", back_populates="class_academic_years")
    sections = relationship("Section", back_populates="class_academic_year", cascade="all, delete-orphan")
