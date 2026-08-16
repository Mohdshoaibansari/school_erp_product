import { api } from './client';
import type {
  ApprovalDTO,
  ClientCreateDTO,
  ClientDTO,
  ClientUpdateDTO,
  InstitutionTypeCreateDTO,
  InstitutionTypeDTO,
  InstitutionTypeUpdateDTO,
  LifecycleTransitionDTO,
  OwnershipTransferApproveDTO,
  OwnershipTransferEventDTO,
  OwnershipTransferRequestDTO,
} from './dto/platform';

export const platformApi = {
  // Clients
  listClients: () => api.get<ClientDTO[]>('/api/v1/platform/clients'),
  getClient: (clientId: string) =>
    api.get<ClientDTO>(`/api/v1/platform/clients/${clientId}`),
  createClient: (payload: ClientCreateDTO) =>
    api.post<ClientDTO>('/api/v1/platform/clients', payload),
  updateClient: (clientId: string, payload: ClientUpdateDTO) =>
    api.patch<ClientDTO>(`/api/v1/platform/clients/${clientId}`, payload),
  transitionClient: (clientId: string, payload: LifecycleTransitionDTO) =>
    api.post<ClientDTO>(
      `/api/v1/platform/clients/${clientId}/transition`,
      payload,
    ),

  // Institution types
  listInstitutionTypes: () =>
    api.get<InstitutionTypeDTO[]>('/api/v1/platform/institution-types'),
  createInstitutionType: (payload: InstitutionTypeCreateDTO) =>
    api.post<InstitutionTypeDTO>('/api/v1/platform/institution-types', payload),
  updateInstitutionType: (
    typeId: string,
    payload: InstitutionTypeUpdateDTO,
  ) =>
    api.patch<InstitutionTypeDTO>(
      `/api/v1/platform/institution-types/${typeId}`,
      payload,
    ),

  // Ownership transfers
  requestOwnershipTransfer: (payload: OwnershipTransferRequestDTO) =>
    api.post<ApprovalDTO>('/api/v1/platform/ownership-transfers', payload),
  approveOwnershipTransfer: (
    approvalId: string,
    toClientId: string,
    payload: OwnershipTransferApproveDTO,
  ) =>
    api.post<OwnershipTransferEventDTO>(
      `/api/v1/platform/ownership-transfers/${approvalId}/approve`,
      payload,
      { params: { to_client_id: toClientId } },
    ),
};
