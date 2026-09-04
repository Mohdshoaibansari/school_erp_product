"""C-05 Academic Structure — Section model.

Year-specific subdivision of a Class. Belongs to ClassAcademicYear.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Integer, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class Section(Base):
    """Section entity — year-specific subdivision of a Class."""

    __tablename__ = "section"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institution.id"), nullable=False)
    class_academic_year_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("class_academic_year.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "A"
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    class_academic_year = relationship("ClassAcademicYear", back_populates="sections")
    section_subjects = relationship("SectionSubject", back_populates="section", cascade="all, delete-orphan")
