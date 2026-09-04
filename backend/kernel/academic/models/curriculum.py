"""C-05 Academic Structure — Curriculum model.

Belongs to GradeLevel. Represents the curriculum framework.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class Curriculum(Base):
    """Curriculum entity — belongs to GradeLevel."""

    __tablename__ = "curriculum"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institution.id"), nullable=False)
    grade_level_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("grade_level.id"), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Grade 11 Curriculum"
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    grade_level = relationship("GradeLevel", back_populates="curriculum")
    versions = relationship("CurriculumVersion", back_populates="curriculum", cascade="all, delete-orphan")
