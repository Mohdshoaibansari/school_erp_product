"""C-05 Academic Structure — Subject model.

Course/discipline (e.g., "Mathematics"). Belongs to CurriculumVersion.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Integer, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class Subject(Base):
    """Subject entity — course/discipline belonging to CurriculumVersion."""

    __tablename__ = "subject"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institution.id"), nullable=False)
    curriculum_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("curriculum_version.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)  # e.g., "Mathematics"
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g., "MATH101"
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    curriculum_version = relationship("CurriculumVersion", back_populates="subjects")
    section_subjects = relationship("SectionSubject", back_populates="subject")
