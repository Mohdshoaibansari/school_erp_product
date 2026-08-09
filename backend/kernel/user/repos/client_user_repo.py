"""ClientUserRepository (task 3.3).

Inherits TenantAwareRepositoryBase[ClientUser]. Methods: create, get_by_id, list_by_client,
get_by_email, update, transition_lifecycle, delete (archive). Returns ClientUserDTO.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.tenant_context import TenantContext
from kernel.user.models.client_user import ClientUser
from kernel.user.models.client_user_lifecycle_event import ClientUserLifecycleEvent
from kernel.repo_base import TenantAwareRepositoryBase
from kernel.user.services.dtos import ClientUserDTO, ClientUserCreateDTO, ClientUserUpdateDTO


class ClientUserRepository(TenantAwareRepositoryBase[ClientUser]):
    """Repository for the ClientUser entity (D1, D3, D10).

    Auto-injects client_id from TenantContext via TenantAwareRepositoryBase.
    PO bypass (D36) skips the tenant filter, letting the PO see all client_user
    rows across all clients. CD access is restricted by client_id (own client)
    at the RLS layer via the own-row policies from migration 011.
    """

    def __init__(self) -> None:
        super().__init__(ClientUser)

    def _to_dto(self, obj: ClientUser) -> ClientUserDTO:
        return ClientUserDTO.model_validate(obj)

    def create(
        self, session: Session, ctx: TenantContext, dto: ClientUserCreateDTO,
        *,
        user_id: uuid.UUID | None = None,
    ) -> ClientUserDTO:
        """Create a new ClientUser (PO-only — no client_id auto-inject;
        the PO sets client_id explicitly in the DTO).

        Args:
            user_id: optional UUID to use as the row's id. When provided (CD bootstrap),
                     uses this so Supabase Auth and the invite JWT share the same id.
                     When None (future self-registration), auto-generates via default=uuid4.
        """
        # Check email uniqueness across client_user
        existing = session.execute(
            select(ClientUser).where(ClientUser.email == dto.email)
        ).scalars().first()
        if existing:
            raise ValueError(f"Email '{dto.email}' is already taken in client_user")

        uid = user_id or uuid.uuid4()
        client_id = ctx.client_id or dto.client_id

        # D12: Insert user_account parent row first
        from sqlalchemy import text as sa_text
        session.execute(sa_text(
            "INSERT INTO user_account (id) VALUES (:id) ON CONFLICT (id) DO NOTHING"
        ), {"id": uid})

        obj = ClientUser(
            id=uid,
            client_id=client_id,
            email=dto.email,
            name=dto.name,
            user_category_id=dto.user_category_id,
            role_id=dto.role_id,
            lifecycle_status="invited",
        )
        session.add(obj)
        session.flush()
        return self._to_dto(obj)

    def get_by_id(
        self, session: Session, ctx: TenantContext, user_id: uuid.UUID,
    ) -> ClientUserDTO | None:
        """Get a ClientUser by ID. PO bypass skips tenant filter;
        CD own-row access is limited to their own ID by the caller."""
        stmt = select(ClientUser).where(ClientUser.id == user_id)
        stmt = self._apply_tenant_filter(stmt, ctx)
        obj = session.execute(stmt).scalars().first()
        return self._to_dto(obj) if obj else None

    def get_by_email(
        self, session: Session, email: str,
    ) -> ClientUserDTO | None:
        """Get a ClientUser by email (not tenant-filtered — email is globally unique)."""
        stmt = select(ClientUser).where(ClientUser.email == email)
        obj = session.execute(stmt).scalars().first()
        return self._to_dto(obj) if obj else None

    def list_by_client(
        self, session: Session, ctx: TenantContext, client_id: uuid.UUID,
    ) -> list[ClientUserDTO]:
        """List all ClientUsers for a given client. PO-only (require_platform_owner gates)."""
        stmt = select(ClientUser).where(ClientUser.client_id == client_id)
        # D36: PO bypass skips tenant filter; non-PO would only see own-client rows
        stmt = self._apply_tenant_filter(stmt, ctx)
        objs = session.execute(stmt).scalars().all()
        return [self._to_dto(obj) for obj in objs]

    def update(
        self, session: Session, ctx: TenantContext, user_id: uuid.UUID,
        dto: ClientUserUpdateDTO,
    ) -> ClientUserDTO:
        """Update ClientUser fields (name, email). CD can update own row;
        PO can update any row."""
        stmt = select(ClientUser).where(ClientUser.id == user_id)
        stmt = self._apply_tenant_filter(stmt, ctx)
        obj = session.execute(stmt).scalars().first()
        if not obj:
            raise ValueError("ClientUser not found")

        data = dto.model_dump(exclude_unset=True)
        if "email" in data and data["email"] != obj.email:
            existing = session.execute(
                select(ClientUser).where(
                    ClientUser.email == data["email"],
                    ClientUser.id != user_id
                )
            ).scalars().first()
            if existing:
                raise ValueError(f"Email '{data['email']}' is already taken")
        for key, value in data.items():
            setattr(obj, key, value)
        session.flush()
        return self._to_dto(obj)

    def transition_lifecycle(
        self, session: Session, ctx: TenantContext, user_id: uuid.UUID,
        new_state: str, reason: str | None, actor: str,
    ) -> ClientUserDTO:
        """Transition ClientUser lifecycle and record a client_user_lifecycle_event row (D10)."""
        stmt = select(ClientUser).where(ClientUser.id == user_id)
        # D36: PO bypass lets the PO transition any CD
        stmt = self._apply_tenant_filter(stmt, ctx)
        obj = session.execute(stmt).scalars().first()
        if not obj:
            raise ValueError("ClientUser not found")

        old_state = obj.lifecycle_status
        obj.lifecycle_status = new_state
        session.flush()

        # Record lifecycle event
        event = ClientUserLifecycleEvent(
            client_user_id=user_id,
            state=new_state,
            reason=reason,
            actor=actor,
        )
        session.add(event)
        session.flush()

        return self._to_dto(obj)

    def delete(
        self, session: Session, ctx: TenantContext, user_id: uuid.UUID,
        actor: str, reason: str | None = None,
    ) -> None:
        """Archive a ClientUser (PO-only). Sets lifecycle_status to 'archived' and records event."""
        stmt = select(ClientUser).where(ClientUser.id == user_id)
        stmt = self._apply_tenant_filter(stmt, ctx)
        obj = session.execute(stmt).scalars().first()
        if not obj:
            raise ValueError("ClientUser not found")

        obj.lifecycle_status = "archived"
        session.flush()

        event = ClientUserLifecycleEvent(
            client_user_id=user_id,
            state="archived",
            reason=reason,
            actor=actor,
        )
        session.add(event)
        session.flush()
