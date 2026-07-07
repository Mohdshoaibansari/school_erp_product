"""C-01 services — published interface (A4).

Endpoints call services; services call repos. This is the module boundary.
"""

from kernel.tenant_institution.services.service import TenantInstitutionService
from kernel.tenant_institution.services.dtos import (
    ApprovalDTO,
    ClientCreateDTO,
    ClientDTO,
    ClientUpdateDTO,
    InstitutionCreateDTO,
    InstitutionDTO,
    InstitutionTypeCreateDTO,
    InstitutionTypeDTO,
    InstitutionTypeUpdateDTO,
    InstitutionUpdateDTO,
    LifecycleTransitionDTO,
    OrgUnitCreateDTO,
    OrgUnitDTO,
    OrgUnitMoveDTO,
    OrgUnitReorderDTO,
    OwnershipTransferApproveDTO,
    OwnershipTransferEventDTO,
    OwnershipTransferRequestDTO,
)
from kernel.tenant_institution.services.state_machine import (
    InvalidTransitionError,
    CLIENT_ARCS,
    CLIENT_STATES,
    CLIENT_TERMINAL_STATES,
    INSTITUTION_ARCS,
    INSTITUTION_STATES,
    INSTITUTION_TERMINAL_STATES,
    validate_client_transition,
    validate_institution_transition,
    is_client_state_terminal,
    is_institution_operationally_active,
)
from kernel.tenant_institution.services.approval import (
    ApprovalNotGrantedError,
    ApprovalDeniedError,
    request_approval,
    approve_approval,
    deny_approval,
    assert_approved,
)
from kernel.tenant_institution.services.transfer import (
    TransferCoordinator,
    DefaultTransferCoordinator,
)
from kernel.tenant_institution.services.audit import (
    AuditEmitter,
    DefaultAuditEmitter,
)

__all__ = [
    "TenantInstitutionService",
    "ApprovalDTO",
    "ClientCreateDTO",
    "ClientDTO",
    "ClientUpdateDTO",
    "InstitutionCreateDTO",
    "InstitutionDTO",
    "InstitutionTypeCreateDTO",
    "InstitutionTypeDTO",
    "InstitutionTypeUpdateDTO",
    "InstitutionUpdateDTO",
    "LifecycleTransitionDTO",
    "OrgUnitCreateDTO",
    "OrgUnitDTO",
    "OrgUnitMoveDTO",
    "OrgUnitReorderDTO",
    "OwnershipTransferApproveDTO",
    "OwnershipTransferEventDTO",
    "OwnershipTransferRequestDTO",
    # State machine (8.1, 8.2, 8.3)
    "InvalidTransitionError",
    "CLIENT_ARCS",
    "CLIENT_STATES",
    "CLIENT_TERMINAL_STATES",
    "INSTITUTION_ARCS",
    "INSTITUTION_STATES",
    "INSTITUTION_TERMINAL_STATES",
    "validate_client_transition",
    "validate_institution_transition",
    "is_client_state_terminal",
    "is_institution_operationally_active",
    # Approval flow (8.4)
    "ApprovalNotGrantedError",
    "ApprovalDeniedError",
    "request_approval",
    "approve_approval",
    "deny_approval",
    "assert_approved",
    # Transfer coordinator (11.2, 11.5, 11.6, 11.7)
    "TransferCoordinator",
    "DefaultTransferCoordinator",
    # Audit emitter (13.x — C-11 boundary)
    "AuditEmitter",
    "DefaultAuditEmitter",
]
