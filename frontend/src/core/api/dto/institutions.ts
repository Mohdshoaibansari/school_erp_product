/**
 * Typed DTOs mirroring the C-01 institution/org-unit backend
 * (business/tenant_institution/services/dtos.py).
 */

export interface InstitutionCreateDTO {
  institution_type_id: string;
  display_name: string;
  legal_name: string | null;
  code: string | null;
  primary_contact_email: string | null;
  primary_contact_phone: string | null;
  established_year: number | null;
  affiliation_number: string | null;
  affiliation_board: string | null;
}

export interface InstitutionUpdateDTO {
  display_name?: string | null;
  legal_name?: string | null;
  code?: string | null;
  primary_contact_email?: string | null;
  primary_contact_phone?: string | null;
  established_year?: number | null;
  affiliation_number?: string | null;
  affiliation_board?: string | null;
}

export interface InstitutionDTO {
  id: string;
  client_id: string;
  institution_type_id: string;
  display_name: string;
  legal_name: string | null;
  code: string | null;
  primary_contact_email: string | null;
  primary_contact_phone: string | null;
  address_id: string | null;
  current_lifecycle_status: string;
  established_year: number | null;
  affiliation_number: string | null;
  affiliation_board: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface OrgUnitCreateDTO {
  institution_id: string;
  parent_id: string | null;
  name: string;
  type_id: string;
  sort_order: number;
  code: string | null;
}

export interface OrgUnitMoveDTO {
  new_parent_id: string | null;
}

export interface OrgUnitReorderDTO {
  sort_order: number;
}

export interface OrgUnitDTO {
  id: string;
  client_id: string;
  institution_id: string;
  parent_id: string | null;
  name: string;
  type_id: string;
  sort_order: number;
  code: string | null;
  current_lifecycle_status: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}
