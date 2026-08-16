import { api } from './client';
import type {
  InstitutionCreateDTO,
  InstitutionDTO,
  InstitutionUpdateDTO,
  OrgUnitCreateDTO,
  OrgUnitDTO,
  OrgUnitMoveDTO,
  OrgUnitReorderDTO,
} from './dto/institutions';
import type { LifecycleTransitionDTO } from './dto/platform';

export const institutionsApi = {
  listInstitutions: (crossInstitution = false) =>
    api.get<InstitutionDTO[]>('/api/v1/institutions', {
      params: crossInstitution ? { cross_institution: true } : {},
    }),
  getInstitution: (institutionId: string) =>
    api.get<InstitutionDTO>(`/api/v1/institutions/${institutionId}`),
  createInstitution: (payload: InstitutionCreateDTO) =>
    api.post<InstitutionDTO>('/api/v1/institutions', payload),
  updateInstitution: (institutionId: string, payload: InstitutionUpdateDTO) =>
    api.patch<InstitutionDTO>(
      `/api/v1/institutions/${institutionId}`,
      payload,
    ),
  transitionInstitution: (
    institutionId: string,
    payload: LifecycleTransitionDTO,
  ) =>
    api.post<InstitutionDTO>(
      `/api/v1/institutions/${institutionId}/transition`,
      payload,
    ),
  goLiveInstitution: (institutionId: string, payload: LifecycleTransitionDTO) =>
    api.post<InstitutionDTO>(
      `/api/v1/institutions/${institutionId}/go-live`,
      payload,
    ),

  // Org units
  listOrgUnits: (institutionId: string, crossInstitution = false) =>
    api.get<OrgUnitDTO[]>('/api/v1/org-units', {
      params: {
        institution_id: institutionId,
        ...(crossInstitution ? { cross_institution: true } : {}),
      },
    }),
  getOrgUnitSubtree: (orgUnitId: string) =>
    api.get<OrgUnitDTO[]>(`/api/v1/org-units/${orgUnitId}/subtree`),
  createOrgUnit: (payload: OrgUnitCreateDTO) =>
    api.post<OrgUnitDTO>('/api/v1/org-units', payload),
  moveOrgUnit: (orgUnitId: string, payload: OrgUnitMoveDTO) =>
    api.post<OrgUnitDTO>(`/api/v1/org-units/${orgUnitId}/move`, payload),
  reorderOrgUnit: (orgUnitId: string, payload: OrgUnitReorderDTO) =>
    api.patch<OrgUnitDTO>(
      `/api/v1/org-units/${orgUnitId}/reorder`,
      payload,
    ),
  archiveOrgUnit: (orgUnitId: string) =>
    api.post<OrgUnitDTO>(`/api/v1/org-units/${orgUnitId}/archive`),
  reactivateOrgUnit: (orgUnitId: string) =>
    api.post<OrgUnitDTO>(`/api/v1/org-units/${orgUnitId}/reactivate`),
};
