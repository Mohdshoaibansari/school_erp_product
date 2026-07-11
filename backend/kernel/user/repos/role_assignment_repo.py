"""RoleAssignmentRepository (task 7.3).

Inherits TenantAwareRepositoryBase[RoleAssignment]. Methods: create, get, list, delete.
Returns RoleAssignmentDTO.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from kernel.tenant_context import TenantContext
from kernel.user.models.role_assignment import RoleAssignment
from kernel.repo_base import TenantAwareRepositoryBase
from kernel.audit import AuditEmitter, DefaultAuditEmitter
from kernel.user.services.dtos import RoleAssignmentCreateDTO, RoleAssignmentDTO


class RoleAssignmentRepository(TenantAwareRepositoryBase[RoleAssignment]):
    """Repository for the RoleAssignment entity (Decision 6, AC-6).

    Auto-injects client_id from TenantContext. Returns RoleAssignmentDTO.
    """

    def __init__(self, audit_emitter: AuditEmitter | None = None) -> None:
        super().__init__(RoleAssignment)
        self._audit = audit_emitter or DefaultAuditEmitter()

    def _to_dto(self, obj: RoleAssignment) -> RoleAssignmentDTO:
        return RoleAssignmentDTO.model_validate(obj)

    def create(
        self, session: Session, ctx: TenantContext, user_id: uuid.UUID, dto: RoleAssignmentCreateDTO,
    ) -> RoleAssignmentDTO:
        """Create a RoleAssignment for a User."""
        obj = RoleAssignment(
            client_id=ctx.client_id,
            user_id=user_id,
            role_id=dto.role_id,
            scope=dto.scope,
        )
        session.add(obj)
        session.flush()

        # C-11 audit emission for role assignment (AC-12)
        self._audit.emit(
            action="role_assignment_created",
            client_id=ctx.client_id,
            institution_id=ctx.institution_id,
            actor=ctx.user_id,
            payload={
                "user_id": str(user_id),
                "role_id": str(dto.role_id),
                "scope": dto.scope,
            },
        )

        return self._to_dto(obj)

    def get_by_id(
        self, session: Session, ctx: TenantContext, assignment_id: uuid.UUID,
    ) -> RoleAssignmentDTO | None:
        """Get a RoleAssignment by id, tenant-filtered."""
        stmt = select(RoleAssignment).where(RoleAssignment.id == assignment_id)
        stmt = self._apply_tenant_filter(stmt, ctx)
        obj = session.execute(stmt).scalars().first()
        return self._to_dto(obj) if obj else None

    def list_by_user(
        self, session: Session, ctx: TenantContext, user_id: uuid.UUID,
    ) -> list[RoleAssignmentDTO]:
        """List RoleAssignments for a User, tenant-filtered."""
        stmt = select(RoleAssignment).where(RoleAssignment.user_id == user_id)
        stmt = self._apply_tenant_filter(stmt, ctx)
        result = session.execute(stmt).scalars().all()
        return [self._to_dto(obj) for obj in result]

    def delete(
        self, session: Session, ctx: TenantContext, assignment_id: uuid.UUID,
    ) -> None:
        """Delete a RoleAssignment, tenant-filtered."""
        stmt = select(RoleAssignment).where(RoleAssignment.id == assignment_id)
        stmt = self._apply_tenant_filter(stmt, ctx)
        obj = session.execute(stmt).scalars().first()
        if not obj:
            raise ValueError("RoleAssignment not found")

        # Capture for audit before deletion
        user_id = obj.user_id
        role_id = obj.role_id
        scope = obj.scope

        session.delete(obj)
        session.flush()

        # C-11 audit emission for role removal (AC-12)
        self._audit.emit(
            action="role_assignment_removed",
            client_id=ctx.client_id,
            institution_id=ctx.institution_id,
            actor=ctx.user_id,
            payload={
                "user_id": str(user_id),
                "role_id": str(role_id),
                "scope": scope,
            },
        )
