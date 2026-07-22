"""Client repository (D4, Q1 — self-visible RLS, no client_id column)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.tenant_context import TenantContext
from business.tenant_institution.models import Client
from kernel.repo_base import TenantAwareRepositoryBase
from kernel.audit import AuditEmitter, DefaultAuditEmitter
from business.tenant_institution.services.dtos import (
    ClientCreateDTO,
    ClientDTO,
    ClientUpdateDTO,
)

# Reserved subdomain labels (D3)
_RESERVED_SLUGS = frozenset({
    "www", "api", "admin", "app", "mail", "auth", "platform", "super",
    "smtp", "ftp", "ns", "ns1", "ns2", "cdn", "staging", "demo",
    "test", "dev", "localhost", "support", "help", "blog",
})


def is_reserved_slug(slug: str) -> bool:
    """Check if a slug is a reserved platform label (D3)."""
    return slug.lower() in _RESERVED_SLUGS


def validate_slug_format(slug: str) -> str | None:
    """Validate slug format (D3). Returns error message or None if valid."""
    import re
    if not slug.islower():
        return "Slug must be lowercase"
    if len(slug) < 3 or len(slug) > 63:
        return "Slug must be 3–63 characters"
    if not re.match(r"^[a-z0-9-]+$", slug):
        return "Slug may only contain [a-z0-9-]"
    if not (slug[0].isalnum() and slug[-1].isalnum()):
        return "Slug must start and end with an alphanumeric character"
    return None


class ClientRepository(TenantAwareRepositoryBase[Client]):
    """Repository for the Client entity (D4, Q1).

    The ``client`` table has no ``client_id`` column (the Client IS the tenant).
    RLS is self-visible: ``id = current_client_id`` (Q1). Platform Owners see all.
    """

    def __init__(self, audit_emitter: AuditEmitter | None = None) -> None:
        super().__init__(Client)
        self._audit = audit_emitter or DefaultAuditEmitter()

    def _to_dto(self, obj: Client) -> ClientDTO:
        return ClientDTO.model_validate(obj)

    def create(self, session: Session, ctx: TenantContext, dto: ClientCreateDTO) -> ClientDTO:
        """Create a new Client (Platform-Owner-only per D11)."""
        # Validate slug
        fmt_err = validate_slug_format(dto.slug)
        if fmt_err:
            raise ValueError(fmt_err)
        if is_reserved_slug(dto.slug):
            raise ValueError("Slug is a reserved platform label")

        obj = Client(
            slug=dto.slug,
            display_name=dto.display_name,
            legal_name=dto.legal_name,
            legal_entity_type_id=dto.legal_entity_type_id,
            tax_registration_number=dto.tax_registration_number,
            primary_contact_email=dto.primary_contact_email,
            primary_contact_phone=dto.primary_contact_phone,
            billing_contact_email=dto.billing_contact_email,
            current_lifecycle_status="prospective",
        )
        session.add(obj)
        try:
            session.flush()
        except Exception as e:
            session.rollback()
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                raise ValueError(f"Slug '{dto.slug}' is already taken")
            raise
        return self._to_dto(obj)

    def get_by_slug(self, session: Session, slug: str) -> ClientDTO | None:
        """Resolve a Client by slug (used by the subdomain middleware, D3).

        This is NOT tenant-filtered — it's the resolver that SETS the tenant context.
        """
        stmt = select(Client).where(Client.slug == slug)
        obj = session.execute(stmt).scalars().first()
        return self._to_dto(obj) if obj else None

    def get_by_id(self, session: Session, ctx: TenantContext, client_id: uuid.UUID) -> ClientDTO | None:
        """Get a Client by id, tenant-filtered (self-visible for non-platform, all for platform)."""
        if ctx.is_platform_owner:
            stmt = select(Client).where(Client.id == client_id)
        else:
            # Self-visible (Q1) — only own client
            stmt = select(Client).where(Client.id == client_id, Client.id == ctx.client_id)
        obj = session.execute(stmt).scalars().first()
        return self._to_dto(obj) if obj else None

    def list_all(self, session: Session, ctx: TenantContext) -> list[ClientDTO]:
        """List clients — Platform Owner sees all; tenant user sees own (Q1, D11)."""
        if ctx.is_platform_owner:
            stmt = select(Client)
        else:
            stmt = select(Client).where(Client.id == ctx.client_id)
        result = session.execute(stmt).scalars().all()
        return [self._to_dto(obj) for obj in result]

    def update_identity(
        self, session: Session, ctx: TenantContext, client_id: uuid.UUID, dto: ClientUpdateDTO,
    ) -> ClientDTO:
        """Update Client identity fields (slug immutable, D3/AC-3)."""
        stmt = select(Client).where(Client.id == client_id)
        if not ctx.is_platform_owner:
            stmt = stmt.where(Client.id == ctx.client_id)
        obj = session.execute(stmt).scalars().first()
        if not obj:
            raise ValueError("Client not found")

        # Slug is immutable — never update it (D3, AC-3)
        data = dto.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(obj, key, value)
        session.flush()
        return self._to_dto(obj)

    def transition_lifecycle(
        self, session: Session, ctx: TenantContext, client_id: uuid.UUID,
        new_state: str, reason: str | None, actor: str,
    ) -> ClientDTO:
        """Transition Client lifecycle (D8 arcs, AC-5).

        Validates the arc via the state machine (task 8.1) and writes a
        ``client_lifecycle_event`` row on every transition (task 8.5).
        C-11 audit emission deferred to Apply-D (task 13.1).
        """
        from business.tenant_institution.services.state_machine import (
            validate_client_transition,
        )

        stmt = select(Client).where(Client.id == client_id)
        obj = session.execute(stmt).scalars().first()
        if not obj:
            raise ValueError("Client not found")

        old_state = obj.current_lifecycle_status
        # Full state-machine validation (D8, task 8.1)
        validate_client_transition(old_state, new_state)

        obj.current_lifecycle_status = new_state
        if new_state == "archived":
            from datetime import datetime, timezone
            obj.archived_at = datetime.now(timezone.utc)
        session.flush()

        # Record lifecycle event (D8, task 8.5) — one row per transition
        from business.tenant_institution.models import ClientLifecycleEvent
        event = ClientLifecycleEvent(
            client_id=obj.id,
            state=new_state,
            reason=reason,
            actor=actor,
        )
        session.add(event)
        session.flush()

        # 13.1: synchronous C-11 audit emission for Client lifecycle transitions
        # (ClientId tagged, AC-5).
        self._audit.emit(
            action="client_lifecycle_transition",
            client_id=obj.id,
            institution_id=None,
            actor=actor,
            payload={
                "client_id": str(obj.id),
                "from_state": old_state,
                "to_state": new_state,
                "reason": reason,
                "actor": actor,
            },
        )

        return self._to_dto(obj)
