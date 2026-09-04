"""C-05 Academic Structure — SectionSubject model.

Represents the applicability of a Subject to a Section.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Boolean, text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class SectionSubject(Base):
    """SectionSubject entity — applicability of a Subject to a Section."""

    __tablename__ = "section_subject"
    __table_args__ = (
        UniqueConstraint("section_id", "subject_id", name="uq_section_subject"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institution.id"), nullable=False)
    section_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("section.id"), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subject.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    section = relationship("Section", back_populates="section_subjects")
    subject = relationship("Subject", back_populates="section_subjects")
