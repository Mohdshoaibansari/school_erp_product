"""UserIdentifierRepository (task 7.4).

Inherits TenantAwareRepositoryBase[UserIdentifier]. Methods: create, get, list, delete.
Returns UserIdentifierDTO.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.tenant_context import TenantContext
from kernel.user.models.user_identifier import UserIdentifier
from kernel.repo_base import TenantAwareRepositoryBase
from kernel.audit import AuditEmitter, DefaultAuditEmitter
from kernel.user.services.dtos import UserIdentifierCreateDTO, UserIdentifierDTO


class UserIdentifierRepository(TenantAwareRepositoryBase[UserIdentifier]):
    """Repository for the UserIdentifier entity (Decision 7, AC-7).

    Auto-injects client_id from TenantContext. Returns UserIdentifierDTO.
    """

    def __init__(self, audit_emitter: AuditEmitter | None = None) -> None:
        super().__init__(UserIdentifier)
        self._audit = audit_emitter or DefaultAuditEmitter()

    def _to_dto(self, obj: UserIdentifier) -> UserIdentifierDTO:
        return UserIdentifierDTO.model_validate(obj)

    def create(
        self, session: Session, ctx: TenantContext, user_id: uuid.UUID, dto: UserIdentifierCreateDTO,
    ) -> UserIdentifierDTO:
        """Create a UserIdentifier for a User."""
        obj = UserIdentifier(
            client_id=ctx.client_id,
            user_id=user_id,
            type=dto.type,
            value=dto.value,
        )
        session.add(obj)
        session.flush()

        # C-11 audit emission for identifier creation (AC-13)
        self._audit.emit(
            action="user_identifier_created",
            client_id=ctx.client_id,
            institution_id=ctx.institution_id,
            actor=ctx.user_id,
            payload={
                "user_id": str(user_id),
                "type": dto.type,
                "value": dto.value,
            },
        )

        return self._to_dto(obj)

    def get_by_id(
        self, session: Session, ctx: TenantContext, identifier_id: uuid.UUID,
    ) -> UserIdentifierDTO | None:
        """Get a UserIdentifier by id, tenant-filtered."""
        stmt = select(UserIdentifier).where(UserIdentifier.id == identifier_id)
        stmt = self._apply_tenant_filter(stmt, ctx)
        obj = session.execute(stmt).scalars().first()
        return self._to_dto(obj) if obj else None

    def list_by_user(
        self, session: Session, ctx: TenantContext, user_id: uuid.UUID,
    ) -> list[UserIdentifierDTO]:
        """List UserIdentifiers for a User, tenant-filtered."""
        stmt = select(UserIdentifier).where(UserIdentifier.user_id == user_id)
        stmt = self._apply_tenant_filter(stmt, ctx)
        result = session.execute(stmt).scalars().all()
        return [self._to_dto(obj) for obj in result]

    def delete(
        self, session: Session, ctx: TenantContext, identifier_id: uuid.UUID,
    ) -> None:
        """Delete a UserIdentifier, tenant-filtered."""
        stmt = select(UserIdentifier).where(UserIdentifier.id == identifier_id)
        stmt = self._apply_tenant_filter(stmt, ctx)
        obj = session.execute(stmt).scalars().first()
        if not obj:
            raise ValueError("UserIdentifier not found")

        # Capture for audit before deletion
        user_id = obj.user_id
        id_type = obj.type
        id_value = obj.value

        session.delete(obj)
        session.flush()

        # C-11 audit emission for identifier deletion (AC-13)
        self._audit.emit(
            action="user_identifier_removed",
            client_id=ctx.client_id,
            institution_id=ctx.institution_id,
            actor=ctx.user_id,
            payload={
                "user_id": str(user_id),
                "type": id_type,
                "value": id_value,
            },
        )
