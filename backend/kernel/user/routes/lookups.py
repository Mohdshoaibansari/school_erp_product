"""C-02 UserCategory and Role lookup routes (task 9.6).

Endpoints for listing user categories and roles.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.user.models.user_category import UserCategory
from kernel.user.models.role import Role
from kernel.user.services.dtos import UserCategoryDTO, RoleDTO
from sqlalchemy import select
from kernel.user.dependencies import get_db_session_factory

router = APIRouter(prefix="/api/v1/lookups", tags=["lookups"])


@router.get("/user-categories", response_model=list[UserCategoryDTO])
def list_user_categories(
    ctx: TenantContext = Depends(get_tenant_context),
) -> list[UserCategoryDTO]:
    """List all UserCategory lookup values."""
    session_factory = get_db_session_factory()
    with session_factory() as session:
        result = session.execute(select(UserCategory)).scalars().all()
        return [UserCategoryDTO.model_validate(obj) for obj in result]


@router.get("/roles", response_model=list[RoleDTO])
def list_roles(
    ctx: TenantContext = Depends(get_tenant_context),
) -> list[RoleDTO]:
    """List all Role lookup values."""
    session_factory = get_db_session_factory()
    with session_factory() as session:
        result = session.execute(select(Role)).scalars().all()
        return [RoleDTO.model_validate(obj) for obj in result]
