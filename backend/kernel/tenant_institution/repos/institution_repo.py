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
        """Transition Institution lifecycle (D9 arcs). Go-live = Onboarding→Active.
        Full state-machine + Approval flow is sub-phase C (task 8).
        """
        stmt = select(Institution).where(
            Institution.id == institution_id,
            Institution.client_id == ctx.client_id,
        )
        obj = session.execute(stmt).scalars().first()
        if not obj:
            raise ValueError("Institution not found")

        old_state = obj.current_lifecycle_status
        # Basic arc validation (D9) — full state machine is task 8.2 (Apply-C)
        _ALLOWED_INSTITUTION_ARCS = {
            ("onboarding", "active"),
            ("onboarding", "archived"),
            ("active", "inactive"),
            ("inactive", "active"),
            ("active", "archived"),
            ("inactive", "archived"),
            ("archived", "active"),
        }
        if (old_state, new_state) not in _ALLOWED_INSTITUTION_ARCS:
            raise ValueError(
                f"Institution lifecycle transition '{old_state}→{new_state}' is not allowed"
            )

        obj.current_lifecycle_status = new_state
        session.flush()

        # Record lifecycle event (D9) — C-11 audit emission deferred to Apply-D (task 13.2)
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
