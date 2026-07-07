"""InstitutionType repository (D7 — JSONB template, configurable via API)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.tenant_context import TenantContext
from kernel.tenant_institution.models import InstitutionType, OrgUnitType
from kernel.tenant_institution.repos.base import TenantAwareRepositoryBase
from kernel.tenant_institution.services.dtos import (
    InstitutionTypeCreateDTO,
    InstitutionTypeDTO,
    InstitutionTypeUpdateDTO,
)


class TemplateValidationError(ValueError):
    """Raised when an InstitutionType JSONB template is invalid (D7, task 10.1)."""


def _extract_template_nodes(template) -> list:
    """Normalize the template into a list of top-level node dicts."""
    if isinstance(template, list):
        return template
    if isinstance(template, dict):
        if "children" in template:
            return template.get("children", [])
        return [template]
    return []


def validate_template(session: Session, template) -> None:
    """Validate a JSONB OrgUnit template (D7, task 10.1).

    Checks:
    1. Every referenced ``org_unit_type`` is a valid OrgUnitType name.
    2. The template tree is acyclic (no node references itself or creates a
       cycle via ``children``).

    Raises ``TemplateValidationError`` on any violation.
    """
    # Load all valid OrgUnit type names
    result = session.execute(select(OrgUnitType))
    valid_type_names = {row.name for row in result.scalars().all()}

    def _check_node(node: dict, path: set[str]) -> None:
        if not isinstance(node, dict):
            raise TemplateValidationError(
                f"Template node must be a dict, got {type(node).__name__}"
            )
        type_name = node.get("org_unit_type")
        if not type_name:
            raise TemplateValidationError(
                "Template node missing 'org_unit_type' field"
            )
        if type_name not in valid_type_names:
            raise TemplateValidationError(
                f"Invalid OrgUnit type '{type_name}' in template — "
                f"not found in org_unit_type lookup table"
            )
        # Cycle detection: use the node's name + type as a path key
        node_key = node.get("name", type_name)
        if node_key in path:
            raise TemplateValidationError(
                f"Template tree contains a cycle at node '{node_key}' "
                f"(path: {' → '.join(path)} → {node_key})"
            )
        children = node.get("children", [])
        if children:
            new_path = path | {node_key}
            for child in children:
                _check_node(child, new_path)

    nodes = _extract_template_nodes(template)
    for node in nodes:
        _check_node(node, set())


class InstitutionTypeRepository(TenantAwareRepositoryBase[InstitutionType]):
    """Repository for the InstitutionType entity (D7).

    InstitutionType is platform-scoped (not tenant-scoped — no ``client_id``
    column). Platform-Owner-only management per D11.
    """

    def __init__(self) -> None:
        super().__init__(InstitutionType)

    @property
    def _is_client_scoped(self) -> bool:
        return False  # InstitutionType has no client_id column

    def _client_filter(self, ctx: TenantContext):
        """No client filter — InstitutionType is platform-scoped."""
        return None

    def _to_dto(self, obj: InstitutionType) -> InstitutionTypeDTO:
        return InstitutionTypeDTO.model_validate(obj)

    def create(
        self, session: Session, ctx: TenantContext, dto: InstitutionTypeCreateDTO,
    ) -> InstitutionTypeDTO:
        """Create an InstitutionType (Platform-Owner-only, D7, D11).

        Validates the JSONB template (task 10.1): referenced OrgUnit types
        must be valid, and the template tree must be acyclic.
        """
        if dto.default_org_unit_template is not None:
            validate_template(session, dto.default_org_unit_template)
        obj = InstitutionType(
            name_id=dto.name_id,
            code=dto.code,
            is_system=dto.is_system,
            default_org_unit_template=dto.default_org_unit_template,
        )
        session.add(obj)
        session.flush()
        return self._to_dto(obj)

    def update_template(
        self, session: Session, ctx: TenantContext, itype_id: uuid.UUID,
        dto: InstitutionTypeUpdateDTO,
    ) -> InstitutionTypeDTO:
        """Update InstitutionType template (D7, task 10.1).

        Validates the JSONB template: referenced OrgUnit types must be valid
        and the template tree must be acyclic.
        """
        stmt = select(InstitutionType).where(InstitutionType.id == itype_id)
        obj = session.execute(stmt).scalars().first()
        if not obj:
            raise ValueError("InstitutionType not found")
        if dto.default_org_unit_template is not None:
            validate_template(session, dto.default_org_unit_template)
            obj.default_org_unit_template = dto.default_org_unit_template
        session.flush()
        return self._to_dto(obj)

    def get(self, session: Session, ctx: TenantContext, itype_id: uuid.UUID) -> InstitutionTypeDTO | None:
        stmt = select(InstitutionType).where(InstitutionType.id == itype_id)
        obj = session.execute(stmt).scalars().first()
        return self._to_dto(obj) if obj else None

    def list_all(self, session: Session, ctx: TenantContext) -> list[InstitutionTypeDTO]:
        stmt = select(InstitutionType)
        result = session.execute(stmt).scalars().all()
        return [self._to_dto(obj) for obj in result]
