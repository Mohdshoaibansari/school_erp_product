"""C-04 Authorization — Permission + RolePermission ORM models (D8, D23, AC-1, AC-2).

``Permission`` is a global catalog of every possible action in the platform.
``RolePermission`` maps C-02 roles (identity labels) to permissions (authz actions).
Both are global lookup tables (no RLS, no client_id column).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Permission(Base):
    """Global permission catalog — one row per granular action.

    Phase 1 seeds 26 rows: 14 C-01 + 12 C-02 permissions.
    """

    __tablename__ = "permission"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, unique=True, nullable=False)  # e.g., "client.create"
    description = Column(Text, nullable=True)           # e.g., "Create a new client"
    resource = Column(String(100), nullable=False)      # e.g., "client"
    action = Column(String(100), nullable=False)        # e.g., "create"
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class RolePermission(Base):
    """Role-to-permission mapping — FK to C-02's ``role`` table (D8).

    Defines which C-02 role labels get which permissions.  Read at startup by
    the policy loader and pushed into the Casbin enforcer (D11, D24).
    """

    __tablename__ = "role_permission"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id = Column(UUID(as_uuid=True), ForeignKey("role.id"), nullable=False)
    permission_id = Column(UUID(as_uuid=True), ForeignKey("permission.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )
