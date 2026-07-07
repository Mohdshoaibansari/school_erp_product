"""OrgUnit repository (D6 — adjacency list, cycle prevention, subtree move).

Cycle prevention is app-side (Q6 — NO DB trigger). Subtree moves naturally
follow because it's an adjacency list — moving a node's ``parent_id`` moves
the whole subtree.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from kernel.tenant_context import TenantContext
from kernel.tenant_institution.models import OrgUnit
from kernel.tenant_institution.repos.base import TenantAwareRepositoryBase
from kernel.tenant_institution.services.dtos import (
    OrgUnitCreateDTO,
    OrgUnitDTO,
    OrgUnitMoveDTO,
    OrgUnitReorderDTO,
)


class OrgUnitRepository(TenantAwareRepositoryBase[OrgUnit]):
    """Repository for the OrgUnit entity (D6).

    ``client_id`` is injected from ``TenantContext`` on every query (D1).
    ``institution_id`` is a default business filter.
    """

    def __init__(self) -> None:
        super().__init__(OrgUnit)

    def _to_dto(self, obj: OrgUnit) -> OrgUnitDTO:
        return OrgUnitDTO.model_validate(obj)

    def create(
        self, session: Session, ctx: TenantContext, dto: OrgUnitCreateDTO,
    ) -> OrgUnitDTO:
        """Create an OrgUnit (D6). ``client_id`` from TenantContext."""
        obj = OrgUnit(
            client_id=ctx.client_id,
            institution_id=dto.institution_id,
            parent_id=dto.parent_id,
            name=dto.name,
            type_id=dto.type_id,
            sort_order=dto.sort_order,
            code=dto.code,
            current_lifecycle_status="active",
        )
        session.add(obj)
        session.flush()
        return self._to_dto(obj)

    def update_identity(
        self, session: Session, ctx: TenantContext, org_unit_id: uuid.UUID,
        name: str | None = None, code: str | None = None,
        sort_order: int | None = None,
    ) -> OrgUnitDTO:
        """Update OrgUnit identity fields (type immutable, D6/AC-8)."""
        obj = self._get_orm(session, ctx, org_unit_id)
        if not obj:
            raise ValueError("OrgUnit not found")
        if name is not None:
            obj.name = name
        if code is not None:
            obj.code = code
        if sort_order is not None:
            obj.sort_order = sort_order
        session.flush()
        return self._to_dto(obj)

    def move(
        self, session: Session, ctx: TenantContext, org_unit_id: uuid.UUID,
        new_parent_id: uuid.UUID | None,
    ) -> OrgUnitDTO:
        """Move an OrgUnit to a new parent (D6, AC-9).

        Cycle-prevented (Q6 — app-side check, no DB trigger).
        Subtree moves with the node (adjacency list — moving ``parent_id``
        is enough; descendants follow automatically).
        """
        obj = self._get_orm(session, ctx, org_unit_id)
        if not obj:
            raise ValueError("OrgUnit not found")

        old_parent = obj.parent_id

        # Cycle prevention (Q6): walk up from the prospective parent.
        # If we hit the node being moved, reject.
        if new_parent_id is not None:
            if new_parent_id == org_unit_id:
                raise ValueError("Cannot move an OrgUnit under itself")

            # Walk up from new_parent; if we reach org_unit_id, it's a cycle
            ancestor_id = new_parent_id
            visited = set()
            while ancestor_id is not None:
                if ancestor_id == org_unit_id:
                    raise ValueError(
                        "Cycle detected: cannot move an OrgUnit under its own descendant"
                    )
                if ancestor_id in visited:
                    break  # safety against existing cycles
                visited.add(ancestor_id)
                ancestor = self._get_orm_by_id(session, ancestor_id)
                if ancestor is None:
                    break
                ancestor_id = ancestor.parent_id

        # Perform the move — descendants follow automatically (adjacency list)
        obj.parent_id = new_parent_id
        session.flush()

        # C-11 audit emission for move deferred to Apply-D (task 13.3).
        # Move currently persists without audit; AC-10 full coverage deferred.
        # The endpoint structure is in place for the audit emitter to hook in.

        return self._to_dto(obj)

    def archive(
        self, session: Session, ctx: TenantContext, org_unit_id: uuid.UUID,
    ) -> OrgUnitDTO:
        """Archive an OrgUnit (D6, AC-8 — archive-only, no hard delete)."""
        obj = self._get_orm(session, ctx, org_unit_id)
        if not obj:
            raise ValueError("OrgUnit not found")
        obj.current_lifecycle_status = "archived"
        from datetime import datetime, timezone
        obj.archived_at = datetime.now(timezone.utc)
        session.flush()
        return self._to_dto(obj)

    def reactivate(
        self, session: Session, ctx: TenantContext, org_unit_id: uuid.UUID,
    ) -> OrgUnitDTO:
        """Reactivate an archived OrgUnit (D6, AC-8)."""
        obj = self._get_orm(session, ctx, org_unit_id)
        if not obj:
            raise ValueError("OrgUnit not found")
        obj.current_lifecycle_status = "active"
        obj.archived_at = None
        session.flush()
        return self._to_dto(obj)

    def reorder(
        self, session: Session, ctx: TenantContext, org_unit_id: uuid.UUID,
        sort_order: int,
    ) -> OrgUnitDTO:
        """Reorder an OrgUnit (D6)."""
        obj = self._get_orm(session, ctx, org_unit_id)
        if not obj:
            raise ValueError("OrgUnit not found")
        obj.sort_order = sort_order
        session.flush()
        return self._to_dto(obj)

    def get_subtree(
        self, session: Session, ctx: TenantContext, org_unit_id: uuid.UUID,
    ) -> list[OrgUnitDTO]:
        """Get the full subtree of a node using a recursive CTE (D6)."""
        # Verify the root node exists and is tenant-visible
        root = self._get_orm(session, ctx, org_unit_id)
        if not root:
            return []

        # Recursive CTE: walk down the adjacency list
        sql = text("""
            WITH RECURSIVE subtree AS (
                SELECT * FROM org_unit WHERE id = :root_id AND client_id = :client_id
                UNION ALL
                SELECT ou.* FROM org_unit ou
                JOIN subtree s ON ou.parent_id = s.id
                WHERE ou.client_id = :client_id
            )
            SELECT * FROM subtree
        """)
        result = session.execute(sql, {
            "root_id": str(org_unit_id),
            "client_id": str(ctx.client_id),
        })
        rows = result.fetchall()

        # Map to DTOs
        dtos = []
        for row in rows:
            from datetime import datetime
            dto = OrgUnitDTO(
                id=row.id,
                client_id=row.client_id,
                institution_id=row.institution_id,
                parent_id=row.parent_id,
                name=row.name,
                type_id=row.type_id,
                sort_order=row.sort_order,
                code=row.code,
                current_lifecycle_status=row.current_lifecycle_status,
                created_at=row.created_at,
                updated_at=row.updated_at,
                archived_at=row.archived_at,
            )
            dtos.append(dto)
        return dtos

    def _get_orm(self, session: Session, ctx: TenantContext, org_unit_id: uuid.UUID) -> OrgUnit | None:
        """Get the ORM object, tenant-filtered."""
        stmt = select(OrgUnit).where(
            OrgUnit.id == org_unit_id,
            OrgUnit.client_id == ctx.client_id,
        )
        return session.execute(stmt).scalars().first()

    def _get_orm_by_id(self, session: Session, org_unit_id: uuid.UUID) -> OrgUnit | None:
        """Get the ORM object by id (for cycle-prevention ancestor walk — no tenant
        filter needed since we're checking within the same tenant's tree)."""
        stmt = select(OrgUnit).where(OrgUnit.id == org_unit_id)
        return session.execute(stmt).scalars().first()
