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

    slug: str = Field(..., min_length=3, max_length=63, description="Unique client slug used in the tenant Host header")
    display_name: str = Field(..., min_length=1, max_length=255, description="Display name of the client")
    legal_name: str = Field(..., min_length=1, max_length=255, description="Legal/registered name of the client")
    legal_entity_type_id: uuid.UUID = Field(..., description="ID of the legal entity type (lookup value)")
    tax_registration_number: str | None = Field(None, description="Tax registration number (optional)")
    primary_contact_email: str = Field(..., min_length=1, max_length=255, description="Primary contact email for the client")
    primary_contact_phone: str | None = Field(None, description="Primary contact phone (optional)")
    billing_contact_email: str | None = Field(None, description="Billing contact email (optional)")


class ClientUpdateDTO(BaseModel):
    """Request body for identity-update on a Client (D4 — slug immutable)."""

    display_name: str | None = Field(None, description="Display name of the client")
    legal_name: str | None = Field(None, description="Legal/registered name of the client")
    tax_registration_number: str | None = Field(None, description="Tax registration number")
    primary_contact_email: str | None = Field(None, description="Primary contact email for the client")
    primary_contact_phone: str | None = Field(None, description="Primary contact phone")
    billing_contact_email: str | None = Field(None, description="Billing contact email")


class ClientDTO(BaseModel):
    """Response DTO for a Client (D4)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Client unique identifier")
    slug: str = Field(..., description="Client slug used in the tenant Host header")
    display_name: str = Field(..., description="Display name of the client")
    legal_name: str = Field(..., description="Legal/registered name of the client")
    legal_entity_type_id: uuid.UUID = Field(..., description="ID of the legal entity type")
    tax_registration_number: str | None = Field(None, description="Tax registration number")
    primary_contact_email: str = Field(..., description="Primary contact email for the client")
    primary_contact_phone: str | None = Field(None, description="Primary contact phone")
    billing_contact_email: str | None = Field(None, description="Billing contact email")
    address_id: uuid.UUID | None = Field(None, description="ID of the client's address record")
    current_lifecycle_status: str = Field(..., description="Current lifecycle status (onboarding/active/suspended/archived)")
    created_at: datetime = Field(..., description="Timestamp when the client was created")
    updated_at: datetime = Field(..., description="Timestamp of the last update")
    archived_at: datetime | None = Field(None, description="Timestamp when the client was archived")


class InstitutionTypeCreateDTO(BaseModel):
    """Request body for creating an InstitutionType (D7)."""

    name_id: uuid.UUID = Field(..., description="ID of the institution type name (lookup value)")
    code: str = Field(..., min_length=1, max_length=50, description="Short code identifying the institution type")
    is_system: bool = Field(False, description="Whether this is a system-defined institution type")
    default_org_unit_template: list | dict | None = Field(None, description="Default org unit tree template for institutions of this type")


class InstitutionTypeUpdateDTO(BaseModel):
    """Request body for updating an InstitutionType (D7)."""

    default_org_unit_template: list | dict | None = Field(None, description="Default org unit tree template for institutions of this type")


class InstitutionTypeDTO(BaseModel):
    """Response DTO for an InstitutionType (D7)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Institution type unique identifier")
    name_id: uuid.UUID = Field(..., description="ID of the institution type name")
    code: str = Field(..., description="Short code identifying the institution type")
    is_system: bool = Field(..., description="Whether this is a system-defined institution type")
    default_org_unit_template: list | dict | None = Field(None, description="Default org unit tree template")
    created_at: datetime = Field(..., description="Timestamp when the institution type was created")
    updated_at: datetime = Field(..., description="Timestamp of the last update")


class InstitutionCreateDTO(BaseModel):
    """Request body for creating an Institution (D5). Client implicit from subdomain."""

    institution_type_id: uuid.UUID = Field(..., description="ID of the institution type (School/College)")
    display_name: str = Field(..., min_length=1, max_length=255, description="Display name of the institution")
    legal_name: str | None = Field(None, description="Legal/registered name of the institution")
    code: str | None = Field(None, description="Short institution code")
    primary_contact_email: str | None = Field(None, description="Primary contact email for the institution")
    primary_contact_phone: str | None = Field(None, description="Primary contact phone")
    established_year: int | None = Field(None, description="Year the institution was established")
    affiliation_number: str | None = Field(None, description="Board/school affiliation number")
    affiliation_board: str | None = Field(None, description="Affiliation board name")


class InstitutionUpdateDTO(BaseModel):
    """Request body for identity-update on an Institution (D5 — type immutable)."""

    display_name: str | None = Field(None, description="Display name of the institution")
    legal_name: str | None = Field(None, description="Legal/registered name of the institution")
    code: str | None = Field(None, description="Short institution code")
    primary_contact_email: str | None = Field(None, description="Primary contact email for the institution")
    primary_contact_phone: str | None = Field(None, description="Primary contact phone")
    established_year: int | None = Field(None, description="Year the institution was established")
    affiliation_number: str | None = Field(None, description="Board/school affiliation number")
    affiliation_board: str | None = Field(None, description="Affiliation board name")


class InstitutionDTO(BaseModel):
    """Response DTO for an Institution (D5)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Institution unique identifier")
    client_id: uuid.UUID = Field(..., description="Owning client unique identifier")
    institution_type_id: uuid.UUID = Field(..., description="ID of the institution type")
    display_name: str = Field(..., description="Display name of the institution")
    legal_name: str | None = Field(None, description="Legal/registered name of the institution")
    code: str | None = Field(None, description="Short institution code")
    primary_contact_email: str | None = Field(None, description="Primary contact email for the institution")
    primary_contact_phone: str | None = Field(None, description="Primary contact phone")
    address_id: uuid.UUID | None = Field(None, description="ID of the institution's address record")
    current_lifecycle_status: str = Field(..., description="Current lifecycle status (onboarding/active/suspended/archived)")
    established_year: int | None = Field(None, description="Year the institution was established")
    affiliation_number: str | None = Field(None, description="Board/school affiliation number")
    affiliation_board: str | None = Field(None, description="Affiliation board name")
    created_at: datetime = Field(..., description="Timestamp when the institution was created")
    updated_at: datetime = Field(..., description="Timestamp of the last update")
    archived_at: datetime | None = Field(None, description="Timestamp when the institution was archived")


class OrgUnitCreateDTO(BaseModel):
    """Request body for creating an OrgUnit (D6)."""

    institution_id: uuid.UUID = Field(..., description="ID of the institution the org unit belongs to")
    parent_id: uuid.UUID | None = Field(None, description="ID of the parent org unit (None for root)")
    name: str = Field(..., min_length=1, max_length=255, description="Name of the org unit")
    type_id: uuid.UUID = Field(..., description="ID of the org unit type (lookup value, immutable after creation)")
    sort_order: int = Field(0, description="Sort order among siblings")
    code: str | None = Field(None, description="Short unique code within the institution")


class OrgUnitMoveDTO(BaseModel):
    """Request body for moving an OrgUnit (D6 — parent change, cycle-prevented)."""

    new_parent_id: uuid.UUID | None = Field(None, description="ID of the new parent org unit (None for root)")


class OrgUnitReorderDTO(BaseModel):
    """Request body for reordering OrgUnits (D6)."""

    sort_order: int = Field(..., description="New sort order among siblings")


class OrgUnitDTO(BaseModel):
    """Response DTO for an OrgUnit (D6)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Org unit unique identifier")
    client_id: uuid.UUID = Field(..., description="Owning client unique identifier")
    institution_id: uuid.UUID = Field(..., description="ID of the institution the org unit belongs to")
    parent_id: uuid.UUID | None = Field(None, description="ID of the parent org unit (None for root)")
    name: str = Field(..., description="Name of the org unit")
    type_id: uuid.UUID = Field(..., description="ID of the org unit type")
    sort_order: int = Field(..., description="Sort order among siblings")
    code: str | None = Field(None, description="Short unique code within the institution")
    current_lifecycle_status: str = Field(..., description="Current lifecycle status (active/inactive/archived)")
    created_at: datetime = Field(..., description="Timestamp when the org unit was created")
    updated_at: datetime = Field(..., description="Timestamp of the last update")
    archived_at: datetime | None = Field(None, description="Timestamp when the org unit was archived")


class LifecycleTransitionDTO(BaseModel):
    """Request body for a lifecycle transition (D8/D9)."""

    new_state: str | None = Field(None, description="Target lifecycle state (e.g., active, suspended, archived)")
    reason: str | None = Field(None, description="Reason for the transition")


class OwnershipTransferRequestDTO(BaseModel):
    """Request body for requesting an ownership transfer (D12)."""

    institution_id: uuid.UUID = Field(..., description="ID of the institution to transfer")
    to_client_id: uuid.UUID = Field(..., description="ID of the destination client")
    reason: str | None = Field(None, description="Reason for the ownership transfer")


class OwnershipTransferApproveDTO(BaseModel):
    """Request body for approving an ownership transfer (D12)."""

    consent_source: bool = Field(False, description="Consent given by the source client")
    consent_dest: bool = Field(False, description="Consent given by the destination client")
    reason: str | None = Field(None, description="Approval note or reason")


class ApprovalDTO(BaseModel):
    """Response DTO for an Approval (Q3)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Approval unique identifier")
    requested_by: str = Field(..., description="Actor who requested the approval")
    approved_by: str | None = Field(None, description="Actor who approved the request")
    status: str = Field(..., description="Approval status (pending/approved/rejected)")
    requested_at: datetime = Field(..., description="Timestamp when the approval was requested")
    approved_at: datetime | None = Field(None, description="Timestamp when the approval was decided")
    context_type: str | None = Field(None, description="Type of the context this approval applies to")
    context_id: uuid.UUID | None = Field(None, description="ID of the context entity")
    reason: str | None = Field(None, description="Approval note or reason")


class OwnershipTransferEventDTO(BaseModel):
    """Response DTO for an OwnershipTransferEvent (D12)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Ownership transfer event unique identifier")
    client_id: uuid.UUID = Field(..., description="Owning client unique identifier")
    from_client_id: uuid.UUID = Field(..., description="Source client unique identifier")
    to_client_id: uuid.UUID = Field(..., description="Destination client unique identifier")
    institution_id: uuid.UUID = Field(..., description="ID of the transferred institution")
    approved_by: str = Field(..., description="Actor who approved the transfer")
    consent_source: bool = Field(..., description="Whether the source client consented")
    consent_dest: bool = Field(..., description="Whether the destination client consented")
    transferred_at: datetime = Field(..., description="Timestamp when the transfer was executed")
    reason: str | None = Field(None, description="Reason for the ownership transfer")
    approval_id: uuid.UUID | None = Field(None, description="ID of the associated approval record")
