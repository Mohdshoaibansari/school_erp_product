import { api } from './client';
import type {
  InstitutionTypeLookupDTO,
  LegalEntityTypeLookupDTO,
  OrgUnitTypeLookupDTO,
  RoleDTO,
  UserCategoryDTO,
} from './dto/lookups';

export const lookupsApi = {
  listUserCategories: () =>
    api.get<UserCategoryDTO[]>('/api/v1/lookups/user-categories'),
  listRoles: () => api.get<RoleDTO[]>('/api/v1/lookups/roles'),
  listInstitutionTypes: () =>
    api.get<InstitutionTypeLookupDTO[]>('/api/v1/lookups/institution-types'),
  listOrgUnitTypes: () =>
    api.get<OrgUnitTypeLookupDTO[]>('/api/v1/lookups/org-unit-types'),
  listLegalEntityTypes: () =>
    api.get<LegalEntityTypeLookupDTO[]>('/api/v1/lookups/legal-entity-types'),
};
