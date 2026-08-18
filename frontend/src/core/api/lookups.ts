import { api } from './client';
import type {
  InstitutionTypeLookupDTO,
  LegalEntityTypeLookupDTO,
  OrgUnitTypeLookupDTO,
  RoleDTO,
} from './dto/lookups';

export const lookupsApi = {
  // listUserCategories REMOVED (T-29, D6a) — user_category table dropped.
  listRoles: () => api.get<RoleDTO[]>('/api/v1/lookups/roles'),
  listInstitutionTypes: () =>
    api.get<InstitutionTypeLookupDTO[]>('/api/v1/lookups/institution-types'),
  listOrgUnitTypes: () =>
    api.get<OrgUnitTypeLookupDTO[]>('/api/v1/lookups/org-unit-types'),
  listLegalEntityTypes: () =>
    api.get<LegalEntityTypeLookupDTO[]>('/api/v1/lookups/legal-entity-types'),
};
