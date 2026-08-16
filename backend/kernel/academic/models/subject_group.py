"""C-05 Academic Structure — SubjectGroup + SubjectGroupMember models (D13).

SubjectGroup: collection of subjects (e.g., "Science Group").
SubjectGroupMember: bridge table for many-to-many Subject ↔ SubjectGroup.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class SubjectGroup(Base):
    """SubjectGroup entity — collection of subjects."""

    __tablename__ = "subject_group"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institution.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)  # e.g., "Science Group"
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    members = relationship("SubjectGroupMember", back_populates="subject_group", cascade="all, delete-orphan")


class SubjectGroupMember(Base):
    """Bridge table: Subject ↔ SubjectGroup (many-to-many)."""

    __tablename__ = "subject_group_member"
    __table_args__ = (
        UniqueConstraint("subject_group_id", "subject_id", name="uq_subject_group_member"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    subject_group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subject_group.id"), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subject.id"), nullable=False)

    # Relationships
    subject_group = relationship("SubjectGroup", back_populates="members")
    subject = relationship("Subject", back_populates="group_memberships")
