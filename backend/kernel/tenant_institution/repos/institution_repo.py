"""Institution repository (D5 — client_id RLS tenant column, institution_id business filter)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.tenant_context import TenantContext
from kernel.tenant_institution.models import Institution, InstitutionType, OrgUnit, OrgUnitType
from kernel.tenant_institution.repos.base import TenantAwareRepositoryBase
from kernel.tenant_institution.services.dtos import (
    InstitutionCreateDTO,
    InstitutionDTO,
    InstitutionUpdateDTO,
)


class InstitutionRepository(TenantAwareRepositoryBase[Institution]):
    """Repository for the Institution entity (D5).

    ``client_id`` is injected from ``TenantContext`` on every query (D1).
    ``institution_id`` is a default business filter, overridable by
    cross-institution roles (D11 — 6.2).
    """

    def __init__(self) -> None:
        super().__init__(Institution)

    def _to_dto(self, obj: Institution) -> InstitutionDTO:
        return InstitutionDTO.model_validate(obj)

    def create(
        self, session: Session, ctx: TenantContext, dto: InstitutionCreateDTO,
    ) -> InstitutionDTO:
        """Create an Institution under the resolved Client (D5).

        ``client_id`` comes from ``TenantContext`` (resolved from the subdomain,
        D3). The caller never passes ``client_id``.
        """
        obj = Institution(
            client_id=ctx.client_id,
            institution_type_id=dto.institution_type_id,
            display_name=dto.display_name,
            legal_name=dto.legal_name,
            code=dto.code,
            primary_contact_email=dto.primary_contact_email,
            primary_contact_phone=dto.primary_contact_phone,
            established_year=dto.established_year,
            affiliation_number=dto.affiliation_number,
            affiliation_board=dto.affiliation_board,
            current_lifecycle_status="onboarding",
        )
        session.add(obj)
        session.flush()

        # Materialize the InstitutionType's default OrgUnit template (D7, AC-16).
        # NOTE: full template materialization (validation, recursive tree walk)
        # is task 10.2 (Apply-C). Here we materialize a flat top-level template
        # if present — the recursive tree walk is deferred.
        self._materialize_template(session, ctx, obj)

        return self._to_dto(obj)

    def _materialize_template(
        self, session: Session, ctx: TenantContext, institution: Institution,
    ) -> None:
        """Materialize the InstitutionType's default_org_unit_template (D7, AC-16).

        Recursively creates OrgUnit rows matching the JSONB template tree.
        Deferred aspects (task 10.1 — template validation, acyclic check) are
        NOT implemented here; this is a best-effort materialization that proves
        the endpoint structure works.
        """
        stmt = select(InstitutionType).where(InstitutionType.id == institution.institution_type_id)
        itype = session.execute(stmt).scalars().first()
        if not itype or not itype.default_org_unit_template:
            return

        def _create_nodes(template_nodes: list[dict], parent_id: uuid.UUID | None) -> None:
            for node in template_nodes:
                type_name = node.get("org_unit_type")
                out_stmt = select(OrgUnitType).where(OrgUnitType.name == type_name)
                out = session.execute(out_stmt).scalars().first()
                if not out:
                    continue  # skip invalid type references — validation is task 10.1
                org = OrgUnit(
                    client_id=ctx.client_id,
                    institution_id=institution.id,
                    parent_id=parent_id,
                    name=node.get("name", type_name),
                    type_id=out.id,
                    sort_order=node.get("sort_order", 0),
                    code=node.get("code"),
                    current_lifecycle_status="active",
                )
                session.add(org)
                session.flush()
                children = node.get("children", [])
                if children:
                    _create_nodes(children, org.id)

        template = itype.default_org_unit_template
        if isinstance(template, list):
            _create_nodes(template, None)
        elif isinstance(template, dict) and "children" in template:
            _create_nodes(template.get("children", []), None)

    def get_effective_state(
        self, session: Session, ctx: TenantContext, institution_id: uuid.UUID,
    ) -> str:
        """Compute the **effective** operational state at runtime (D9, AC-7, task 8.3).

        An Institution is operationally Active only if BOTH its own
        ``current_lifecycle_status`` is ``active`` AND its Client's
        ``current_lifecycle_status`` is ``active``.

        This is a **runtime** computation — it does NOT mutate any persisted
        state. When a Client is suspended, the Institution's row is untouched;
        this method returns ``"gated"`` instead of ``"active"``. When the
        Client is restored, it returns ``"active"`` again with no persisted
        state restoration needed (AC-7).

        Returns:
            - ``"active"`` if both Institution and Client are active.
            - ``"gated"`` if the Institution's own state is active but the
              Client is not active (runtime gating — AC-7).
            - The Institution's own ``current_lifecycle_status`` otherwise
              (onboarding, inactive, archived).
        """
        from kernel.tenant_institution.services.state_machine import (
            is_institution_operationally_active,
        )
        from kernel.tenant_institution.models import Client

        stmt = select(Institution).where(
            Institution.id == institution_id,
            Institution.client_id == ctx.client_id,
        )
        inst = session.execute(stmt).scalars().first()
        if not inst:
            raise ValueError("Institution not found")

        # If the institution's own state is not "active", return it directly
        if inst.current_lifecycle_status != "active":
            return inst.current_lifecycle_status

        # Look up the Client's state (no tenant filter — platform-level lookup)
        client_stmt = select(Client).where(Client.id == inst.client_id)
        client = session.execute(client_stmt).scalars().first()
        if not client:
            raise ValueError("Client not found for institution")

        if is_institution_operationally_active(
            inst.current_lifecycle_status, client.current_lifecycle_status,
        ):
            return "active"
        # Institution is active but Client is not — runtime gated (AC-7)
        return "gated"

    def get_client_lifecycle_status(
        self, session: Session, institution_id: uuid.UUID,
    ) -> str:
        """Get the Client's lifecycle status for an Institution (runtime effective-state, AC-7).

        Used by the effective-state computation (task 8.3). No tenant filter —
        this is a platform-level lookup for the gating computation.
        """
        from kernel.tenant_institution.models import Client

        stmt = select(Institution).where(Institution.id == institution_id)
        inst = session.execute(stmt).scalars().first()
        if not inst:
            raise ValueError("Institution not found")

        client_stmt = select(Client).where(Client.id == inst.client_id)
        client = session.execute(client_stmt).scalars().first()
        if not client:
            raise ValueError("Client not found")
        return client.current_lifecycle_status

    def update_identity(
        self, session: Session, ctx: TenantContext, institution_id: uuid.UUID,
        dto: InstitutionUpdateDTO,
    ) -> InstitutionDTO:
        """Update Institution identity fields (institution_type_id immutable, D7/AC-16)."""
        stmt = select(Institution).where(
            Institution.id == institution_id,
            Institution.client_id == ctx.client_id,
        )
        obj = session.execute(stmt).scalars().first()
        if not obj:
            raise ValueError("Institution not found")

        data = dto.model_dump(exclude_unset=True)
        # institution_type_id is immutable after creation (D7, AC-16)
        data.pop("institution_type_id", None)
        for key, value in data.items():
            setattr(obj, key, value)
        session.flush()
        return self._to_dto(obj)

    def transition_lifecycle(
        self, session: Session, ctx: TenantContext, institution_id: uuid.UUID,
        new_state: str, reason: str | None, actor: str,
    ) -> InstitutionDTO:
        """Transition Institution lifecycle (D9 arcs, AC-6).

        Validates the arc via the state machine (task 8.2) and writes an
        ``institution_lifecycle_event`` row on every transition (task 8.5).
        C-11 audit emission deferred to Apply-D (task 13.2).
        """
        from kernel.tenant_institution.services.state_machine import (
            validate_institution_transition,
        )

        stmt = select(Institution).where(
            Institution.id == institution_id,
            Institution.client_id == ctx.client_id,
        )
        obj = session.execute(stmt).scalars().first()
        if not obj:
            raise ValueError("Institution not found")

        old_state = obj.current_lifecycle_status
        # Full state-machine validation (D9, task 8.2) — no Terminated for institutions
        validate_institution_transition(old_state, new_state)

        obj.current_lifecycle_status = new_state
        session.flush()

        # Record lifecycle event (D9, task 8.5) — one row per transition
        from kernel.tenant_institution.models import InstitutionLifecycleEvent
        event = InstitutionLifecycleEvent(
            client_id=obj.client_id,
            institution_id=obj.id,
            state=new_state,
            reason=reason,
            actor=actor,
        )
        session.add(event)
        session.flush()

        return self._to_dto(obj)
