"""Pydantic DTOs for the C-01 tenant-institution domain (tech-stack ADR §3).

Repos convert ORM → DTO at the boundary. Endpoints accept/respond with DTOs.
This is the lazy-load-tenant-bypass prevention: ORM objects never cross the
repository boundary.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ClientCreateDTO(BaseModel):
    """Request body for creating a Client (D4)."""

    slug: str = Field(..., min_length=3, max_length=63)
    display_name: str = Field(..., min_length=1, max_length=255)
    legal_name: str = Field(..., min_length=1, max_length=255)
    legal_entity_type_id: uuid.UUID
    tax_registration_number: str | None = None
    primary_contact_email: str = Field(..., min_length=1, max_length=255)
    primary_contact_phone: str | None = None
    billing_contact_email: str | None = None


class ClientUpdateDTO(BaseModel):
    """Request body for identity-update on a Client (D4 — slug immutable)."""

    display_name: str | None = None
    legal_name: str | None = None
    tax_registration_number: str | None = None
    primary_contact_email: str | None = None
    primary_contact_phone: str | None = None
    billing_contact_email: str | None = None


class ClientDTO(BaseModel):
    """Response DTO for a Client (D4)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    display_name: str
    legal_name: str
    legal_entity_type_id: uuid.UUID
    tax_registration_number: str | None
    primary_contact_email: str
    primary_contact_phone: str | None
    billing_contact_email: str | None
    address_id: uuid.UUID | None
    current_lifecycle_status: str
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class InstitutionTypeCreateDTO(BaseModel):
    """Request body for creating an InstitutionType (D7)."""

    name_id: uuid.UUID
    code: str = Field(..., min_length=1, max_length=50)
    is_system: bool = False
    default_org_unit_template: list | dict | None = None


class InstitutionTypeUpdateDTO(BaseModel):
    """Request body for updating an InstitutionType (D7)."""

    default_org_unit_template: list | dict | None = None


class InstitutionTypeDTO(BaseModel):
    """Response DTO for an InstitutionType (D7)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name_id: uuid.UUID
    code: str
    is_system: bool
    default_org_unit_template: list | dict | None
    created_at: datetime
    updated_at: datetime


class InstitutionCreateDTO(BaseModel):
    """Request body for creating an Institution (D5). Client implicit from subdomain."""

    institution_type_id: uuid.UUID
    display_name: str = Field(..., min_length=1, max_length=255)
    legal_name: str | None = None
    code: str | None = None
    primary_contact_email: str | None = None
    primary_contact_phone: str | None = None
    established_year: int | None = None
    affiliation_number: str | None = None
    affiliation_board: str | None = None


class InstitutionUpdateDTO(BaseModel):
    """Request body for identity-update on an Institution (D5 — type immutable)."""

    display_name: str | None = None
    legal_name: str | None = None
    code: str | None = None
    primary_contact_email: str | None = None
    primary_contact_phone: str | None = None
    established_year: int | None = None
    affiliation_number: str | None = None
    affiliation_board: str | None = None


class InstitutionDTO(BaseModel):
    """Response DTO for an Institution (D5)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    institution_type_id: uuid.UUID
    display_name: str
    legal_name: str | None
    code: str | None
    primary_contact_email: str | None
    primary_contact_phone: str | None
    address_id: uuid.UUID | None
    current_lifecycle_status: str
    established_year: int | None
    affiliation_number: str | None
    affiliation_board: str | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class OrgUnitCreateDTO(BaseModel):
    """Request body for creating an OrgUnit (D6)."""

    institution_id: uuid.UUID
    parent_id: uuid.UUID | None = None
    name: str = Field(..., min_length=1, max_length=255)
    type_id: uuid.UUID
    sort_order: int = 0
    code: str | None = None


class OrgUnitMoveDTO(BaseModel):
    """Request body for moving an OrgUnit (D6 — parent change, cycle-prevented)."""

    new_parent_id: uuid.UUID | None = None


class OrgUnitReorderDTO(BaseModel):
    """Request body for reordering OrgUnits (D6)."""

    sort_order: int


class OrgUnitDTO(BaseModel):
    """Response DTO for an OrgUnit (D6)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    institution_id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    type_id: uuid.UUID
    sort_order: int
    code: str | None
    current_lifecycle_status: str
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class LifecycleTransitionDTO(BaseModel):
    """Request body for a lifecycle transition (D8/D9)."""

    new_state: str | None = None
    reason: str | None = None


class OwnershipTransferRequestDTO(BaseModel):
    """Request body for requesting an ownership transfer (D12)."""

    institution_id: uuid.UUID
    to_client_id: uuid.UUID
    reason: str | None = None


class OwnershipTransferApproveDTO(BaseModel):
    """Request body for approving an ownership transfer (D12)."""

    consent_source: bool = False
    consent_dest: bool = False
    reason: str | None = None


class ApprovalDTO(BaseModel):
    """Response DTO for an Approval (Q3)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    requested_by: str
    approved_by: str | None
    status: str
    requested_at: datetime
    approved_at: datetime | None
    context_type: str | None
    context_id: uuid.UUID | None
    reason: str | None


class OwnershipTransferEventDTO(BaseModel):
    """Response DTO for an OwnershipTransferEvent (D12)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    from_client_id: uuid.UUID
    to_client_id: uuid.UUID
    institution_id: uuid.UUID
    approved_by: str
    consent_source: bool
    consent_dest: bool
    transferred_at: datetime
    reason: str | None
    approval_id: uuid.UUID | None
