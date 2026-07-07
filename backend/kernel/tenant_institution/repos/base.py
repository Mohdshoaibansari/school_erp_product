"""Tenant-aware repository base (D1, A6, task 6.1).

Business logic NEVER passes ``client_id``, never writes SQL. The repository
injects ``client_id`` from the ``TenantContext`` into every tenant-scoped query.
Repos return **DTOs, not ORM objects** (tech-stack ADR §3 — prevents
lazy-load tenant bypass).

Repos are module-scoped singletons (A6); ``TenantContext`` is request-scoped
via ``Depends``.
"""

from __future__ import annotations

import uuid
from typing import Any, Generic, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.tenant_context import TenantContext

from kernel.tenant_institution.models import Client, Institution, OrgUnit

ModelT = TypeVar("ModelT")


class TenantAwareRepositoryBase(Generic[ModelT]):
    """Base class for tenant-scoped repositories (D1).

    Subclasses bind a specific ORM model and provide DTO conversion.
    ``client_id`` is injected from ``TenantContext`` on every query —
    the caller never passes it.
    """

    def __init__(self, model: Type[ModelT]) -> None:
        self._model = model

    @property
    def _is_client_scoped(self) -> bool:
        """Whether the model has a ``client_id`` column (tenant-scoped table).

        The ``client`` table itself has NO ``client_id`` column (Q1) — it
        uses ``id = current_client_id`` RLS instead.
        """
        return self._model is not Client

    def _client_filter(self, ctx: TenantContext):
        """Return the SQLAlchemy filter clause that enforces ``client_id``."""
        if self._is_client_scoped:
            return self._model.client_id == ctx.client_id
        # Client table — self-visible (Q1)
        return self._model.id == ctx.client_id

    def _institution_filter(self, ctx: TenantContext):
        """Return the ``institution_id`` default business filter (D1, 6.2).

        Returns ``None`` if the model has no ``institution_id`` column.
        """
        if hasattr(self._model, "institution_id"):
            return self._model.institution_id == ctx.institution_id
        return None

    def _apply_tenant_filter(self, stmt, ctx: TenantContext, *, cross_institution: bool = False):
        """Inject ``client_id`` (always) + ``institution_id`` (default business filter).

        ``cross_institution=True`` omits the ``institution_id`` default filter
        for authorized cross-institution roles (D11 — Client Director etc.).
        """
        stmt = stmt.where(self._client_filter(ctx))
        if not cross_institution:
            inst_filter = self._institution_filter(ctx)
            if inst_filter is not None and ctx.institution_id is not None:
                stmt = stmt.where(inst_filter)
        return stmt

    def list(
        self,
        session: Session,
        ctx: TenantContext,
        *,
        cross_institution: bool = False,
        **filters: Any,
    ) -> list[Any]:
        """List entities, tenant-filtered. Returns DTOs (not ORM objects)."""
        stmt = select(self._model)
        stmt = self._apply_tenant_filter(stmt, ctx, cross_institution=cross_institution)
        for key, value in filters.items():
            if value is not None and hasattr(self._model, key):
                stmt = stmt.where(getattr(self._model, key) == value)
        result = session.execute(stmt).scalars().all()
        return [self._to_dto(obj) for obj in result]

    def get(self, session: Session, ctx: TenantContext, entity_id: uuid.UUID) -> Any | None:
        """Get a single entity by id, tenant-filtered. Returns DTO or None."""
        stmt = select(self._model).where(self._model.id == entity_id)
        stmt = self._apply_tenant_filter(stmt, ctx)
        obj = session.execute(stmt).scalars().first()
        return self._to_dto(obj) if obj else None

    def _to_dto(self, obj: ModelT) -> Any:
        """Convert ORM → DTO. Subclasses MUST override."""
        raise NotImplementedError

    def _orm_to_dict(self, obj: ModelT) -> dict:
        """Helper: extract column values from an ORM object into a dict."""
        return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
