/**
 * Typed DTOs mirroring the C-01 tenant-institution backend
 * (business/tenant_institution/services/dtos.py).
 */

export interface ClientCreateDTO {
  slug: string;
  display_name: string;
  legal_name: string;
  legal_entity_type_id: string;
  tax_registration_number: string | null;
  primary_contact_email: string;
  primary_contact_phone: string | null;
  billing_contact_email: string | null;
}

export interface ClientUpdateDTO {
  display_name?: string | null;
  legal_name?: string | null;
  tax_registration_number?: string | null;
  primary_contact_email?: string | null;
  primary_contact_phone?: string | null;
  billing_contact_email?: string | null;
}

export interface ClientDTO {
  id: string;
  slug: string;
  display_name: string;
  legal_name: string;
  legal_entity_type_id: string;
  tax_registration_number: string | null;
  primary_contact_email: string;
  primary_contact_phone: string | null;
  billing_contact_email: string | null;
  address_id: string | null;
  current_lifecycle_status: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface InstitutionTypeCreateDTO {
  name_id: string;
  code: string;
  is_system: boolean;
  default_org_unit_template: unknown;
}

export interface InstitutionTypeUpdateDTO {
  default_org_unit_template: unknown;
}

export interface InstitutionTypeDTO {
  id: string;
  name_id: string;
  code: string;
  is_system: boolean;
  default_org_unit_template: unknown;
  created_at: string;
  updated_at: string;
}

export interface LifecycleTransitionDTO {
  new_state: string | null;
  reason: string | null;
}

export interface OwnershipTransferRequestDTO {
  institution_id: string;
  to_client_id: string;
  reason: string | null;
}

export interface OwnershipTransferApproveDTO {
  consent_source: boolean;
  consent_dest: boolean;
  reason: string | null;
}

export interface ApprovalDTO {
  id: string;
  requested_by: string;
  approved_by: string | null;
  status: string;
  requested_at: string;
  approved_at: string | null;
  context_type: string | null;
  context_id: string | null;
  reason: string | null;
}

export interface OwnershipTransferEventDTO {
  id: string;
  client_id: string;
  from_client_id: string;
  to_client_id: string;
  institution_id: string;
  approved_by: string;
  consent_source: boolean;
  consent_dest: boolean;
  transferred_at: string;
  reason: string | null;
  approval_id: string | null;
}
