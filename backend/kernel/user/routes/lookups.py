"""C-02 UserCategory, Role, and InstitutionType lookup routes (task 9.6).

Endpoints for listing user categories, roles, and institution types.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from kernel.user.models.user_category import UserCategory
from kernel.user.models.role import Role
from kernel.user.services.dtos import UserCategoryDTO, RoleDTO
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from kernel.user.dependencies import get_db_session_factory

router = APIRouter(prefix="/api/v1/lookups", tags=["lookups"])


class InstitutionTypeLookupDTO(BaseModel):
    """Minimal DTO for institution type dropdown."""
    id: str = Field(..., description="Institution type ID")
    code: str | None = Field(None, description="Institution type code")

    model_config = {"from_attributes": True}

class OrgUnitTypeLookupDTO(BaseModel):
    """Minimal DTO for org unit type dropdown."""
    id: str = Field(..., description="Org unit type ID")
    name: str = Field(..., description="Org unit type name")

    model_config = {"from_attributes": True}

class LegalEntityTypeLookupDTO(BaseModel):
    """Minimal DTO for legal entity type dropdown."""
    id: str = Field(..., description="Legal entity type ID")
    name: str = Field(..., description="Legal entity type name")

    model_config = {"from_attributes": True}


@router.get("/user-categories", response_model=list[UserCategoryDTO], summary="List user categories")
def list_user_categories(
    _authz: None = Depends(require_permission("user", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
) -> list[UserCategoryDTO]:
    """List all UserCategory lookup values."""
    session_factory = get_db_session_factory()
    with session_factory() as session:
        result = session.execute(select(UserCategory)).scalars().all()
        return [UserCategoryDTO.model_validate(obj) for obj in result]


@router.get("/roles", response_model=list[RoleDTO], summary="List roles")
def list_roles(
    _authz: None = Depends(require_permission("role_assignment", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
) -> list[RoleDTO]:
    """List all Role lookup values."""
    session_factory = get_db_session_factory()
    with session_factory() as session:
        result = session.execute(select(Role)).scalars().all()
        return [RoleDTO.model_validate(obj) for obj in result]


@router.get("/institution-types", response_model=list[InstitutionTypeLookupDTO], summary="List institution types")
def list_institution_types(
    _authz: None = Depends(require_permission("institution", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
) -> list[InstitutionTypeLookupDTO]:
    """List all InstitutionType values available for institution creation.

    Accessible to any authenticated user — needed for institution creation UI.
    Uses raw SQL to avoid kernel→business import.
    """
    session_factory = get_db_session_factory()
    with session_factory() as session:
        result = session.execute(text("SELECT id, code FROM institution_type"))
        return [
            InstitutionTypeLookupDTO(id=str(row[0]), code=row[1])
            for row in result.fetchall()
        ]


@router.get("/org-unit-types", response_model=list[OrgUnitTypeLookupDTO], summary="List org unit types")
def list_org_unit_types(
    _authz: None = Depends(require_permission("org_unit", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
) -> list[OrgUnitTypeLookupDTO]:
    """List all OrgUnitType values available for org unit creation.

    Accessible to any authenticated user — needed for org unit creation UI.
    Uses raw SQL to avoid kernel→business import.
    """
    session_factory = get_db_session_factory()
    with session_factory() as session:
        result = session.execute(text("SELECT id, name FROM org_unit_type ORDER BY name"))
        return [
            OrgUnitTypeLookupDTO(id=str(row[0]), name=row[1])
            for row in result.fetchall()
        ]

@router.get("/legal-entity-types", response_model=list[LegalEntityTypeLookupDTO], summary="List legal entity types")
def list_legal_entity_types(
    _authz: None = Depends(require_permission("client", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
) -> list[LegalEntityTypeLookupDTO]:
    """List all LegalEntityType values available for client creation.

    Accessible to any authenticated user — needed for client creation UI.
    Uses raw SQL to avoid kernel→business import.
    """
    session_factory = get_db_session_factory()
    with session_factory() as session:
        result = session.execute(text("SELECT id, name FROM legal_entity_type ORDER BY name"))
        return [
            LegalEntityTypeLookupDTO(id=str(row[0]), name=row[1])
            for row in result.fetchall()
        ]
