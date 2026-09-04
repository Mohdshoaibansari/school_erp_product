"""C-05 Academic Structure — Term model.

Academic sub-division within an AcademicYear.
Each year owns its own terms (not reusable across years).
Status is computed dynamically (no status column).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, String, Integer, Date, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class Term(Base):
    """Term entity — academic sub-division (e.g., "Term 1 Apr-Sep")."""

    __tablename__ = "term"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institution.id"), nullable=False)
    academic_year_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic_year.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Term 1"
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    academic_year = relationship("AcademicYear", back_populates="terms")

    @property
    def status(self) -> str:
        """Compute status dynamically based on dates."""
        today = date.today()
        if today < self.start_date:
            return "planned"
        elif today <= self.end_date:
            return "active"
        else:
            return "completed"
