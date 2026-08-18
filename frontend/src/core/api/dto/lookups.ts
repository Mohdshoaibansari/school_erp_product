/**
 * Typed DTOs mirroring the C-02 lookups backend
 * (kernel/user/routes/lookups.py).
 *
 * UserCategoryDTO removed (T-29, D6a) — user_category table dropped.
 */

export interface RoleDTO {
  id: string;
  name: string;
}

export interface InstitutionTypeLookupDTO {
  id: string;
  code: string | null;
}

export interface OrgUnitTypeLookupDTO {
  id: string;
  name: string;
}

export interface LegalEntityTypeLookupDTO {
  id: string;
  name: string;
}
