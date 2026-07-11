"""RoleAssignment model (Decision 6, AC-6).

Links User + Role + Scope. Institution comes from the User record —
RoleAssignment does NOT store institution_id. A user can hold multiple
RoleAssignments at the same institution (e.g., Teacher + HOD).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kernel.db import Base


class RoleAssignment(Base):
    """Role assignment — user + role + scope."""

    __tablename__ = "role_assignment"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("role.id"), nullable=False)
    scope: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    user = relationship("User", back_populates="role_assignments")
    role = relationship("Role", foreign_keys=[role_id])
