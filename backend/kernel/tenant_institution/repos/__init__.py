"""C-01 tenant-institution repositories (D1, A6).

Repos are module-scoped singletons (A6). They inject ``client_id`` from
``TenantContext`` into every tenant-scoped query and return **DTOs, not ORM
objects** (tech-stack ADR §3).
"""

from kernel.tenant_institution.repos.base import TenantAwareRepositoryBase
from kernel.tenant_institution.repos.client_repo import (
    ClientRepository,
    is_reserved_slug,
    validate_slug_format,
)
from kernel.tenant_institution.repos.institution_repo import InstitutionRepository
from kernel.tenant_institution.repos.institution_type_repo import InstitutionTypeRepository
from kernel.tenant_institution.repos.org_unit_repo import OrgUnitRepository
from kernel.tenant_institution.repos.approval_transfer_repo import (
    ApprovalRepository,
    OwnershipTransferRepository,
)

__all__ = [
    "TenantAwareRepositoryBase",
    "ClientRepository",
    "InstitutionRepository",
    "InstitutionTypeRepository",
    "OrgUnitRepository",
    "ApprovalRepository",
    "OwnershipTransferRepository",
    "is_reserved_slug",
    "validate_slug_format",
]
