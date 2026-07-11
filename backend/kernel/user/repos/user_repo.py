"""UserRepository (task 7.1).

Inherits TenantAwareRepositoryBase[User]. Methods: create, get, list, update, transition_lifecycle.
Auto-injects client_id from TenantContext. Returns UserDTO.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.tenant_context import TenantContext
from kernel.user.models.user import User
from kernel.repo_base import TenantAwareRepositoryBase
from kernel.audit import AuditEmitter, DefaultAuditEmitter
from kernel.user.services.dtos import UserCreateDTO, UserDTO, UserUpdateDTO


class UserRepository(TenantAwareRepositoryBase[User]):
    """Repository for the User entity (Decision 1, Decision 4).

    Auto-injects client_id from TenantContext. Returns UserDTO.
    """

    def __init__(self, audit_emitter: AuditEmitter | None = None) -> None:
        super().__init__(User)
        self._audit = audit_emitter or DefaultAuditEmitter()

    def _to_dto(self, obj: User) -> UserDTO:
        return UserDTO.model_validate(obj)

    def create(self, session: Session, ctx: TenantContext, dto: UserCreateDTO) -> UserDTO:
        """Create a new User."""
        # Check email uniqueness
        existing = session.execute(
            select(User).where(User.email == dto.email)
        ).scalars().first()
        if existing:
            raise ValueError(f"Email '{dto.email}' is already taken")

        obj = User(
            client_id=ctx.client_id,
            institution_id=dto.institution_id,
            email=dto.email,
            name=dto.name,
            user_category_id=dto.user_category_id,
            lifecycle_status="invited",
        )
        session.add(obj)
        session.flush()
        return self._to_dto(obj)

    def get_by_email(self, session: Session, email: str) -> UserDTO | None:
        """Get a User by email (not tenant-filtered — email is globally unique)."""
        stmt = select(User).where(User.email == email)
        obj = session.execute(stmt).scalars().first()
        return self._to_dto(obj) if obj else None

    def update(
        self, session: Session, ctx: TenantContext, user_id: uuid.UUID, dto: UserUpdateDTO,
    ) -> UserDTO:
        """Update User identity fields (email immutable)."""
        stmt = select(User).where(User.id == user_id)
        stmt = self._apply_tenant_filter(stmt, ctx)
        obj = session.execute(stmt).scalars().first()
        if not obj:
            raise ValueError("User not found")

        data = dto.model_dump(exclude_unset=True)
        # Email is immutable — never update it
        data.pop("email", None)
        for key, value in data.items():
            setattr(obj, key, value)
        session.flush()
        return self._to_dto(obj)

    def transition_lifecycle(
        self, session: Session, ctx: TenantContext, user_id: uuid.UUID,
        new_state: str, reason: str | None, actor: str,
    ) -> UserDTO:
        """Transition User lifecycle (Decision 8, AC-10, AC-11).

        Validates the arc via the state machine and writes a
        user_lifecycle_event row on every transition.
        C-11 audit emission via AuditEmitter Protocol.
        """
        from kernel.user.services.state_machine import validate_user_transition

        stmt = select(User).where(User.id == user_id)
        stmt = self._apply_tenant_filter(stmt, ctx)
        obj = session.execute(stmt).scalars().first()
        if not obj:
            raise ValueError("User not found")

        old_state = obj.lifecycle_status
        validate_user_transition(old_state, new_state)

        obj.lifecycle_status = new_state
        session.flush()

        # Record lifecycle event (Decision 8) — one row per transition
        from kernel.user.models.user_lifecycle_event import UserLifecycleEvent
        event = UserLifecycleEvent(
            client_id=obj.client_id,
            user_id=obj.id,
            state=new_state,
            reason=reason,
            actor=actor,
        )
        session.add(event)
        session.flush()

        # C-11 audit emission for User lifecycle transitions (AC-10)
        self._audit.emit(
            action="user_lifecycle_transition",
            client_id=obj.client_id,
            institution_id=obj.institution_id,
            actor=actor,
            payload={
                "user_id": str(obj.id),
                "from_state": old_state,
                "to_state": new_state,
                "reason": reason,
                "actor": actor,
            },
        )

        return self._to_dto(obj)
