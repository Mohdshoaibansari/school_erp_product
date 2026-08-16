import { api } from './client';
import type {
  ClientUserCreateDTO,
  ClientUserCreateResponseDTO,
  ClientUserDTO,
  ClientUserTransitionDTO,
  ClientUserUpdateDTO,
  RoleAssignmentCreateDTO,
  RoleAssignmentDTO,
  UserCreateDTO,
  UserCreateResponseDTO,
  UserDTO,
  UserIdentifierCreateDTO,
  UserIdentifierDTO,
  UserLifecycleTransitionDTO,
  UserProfileCreateDTO,
  UserProfileDTO,
  UserProfileUpdateDTO,
  UserUpdateDTO,
} from './dto/users';

export const usersApi = {
  // Users (scoped to client/institution)
  listUsers: (filters?: { user_category_id?: string; lifecycle_status?: string }) =>
    api.get<UserDTO[]>('/api/v1/users', { params: filters ?? {} }),
  getUser: (userId: string) => api.get<UserDTO>(`/api/v1/users/${userId}`),
  createUser: (payload: UserCreateDTO) =>
    api.post<UserCreateResponseDTO>('/api/v1/users', payload),
  updateUser: (userId: string, payload: UserUpdateDTO) =>
    api.patch<UserDTO>(`/api/v1/users/${userId}`, payload),
  deleteUser: (userId: string) => api.delete(`/api/v1/users/${userId}`),
  transitionUser: (userId: string, payload: UserLifecycleTransitionDTO) =>
    api.post<UserDTO>(`/api/v1/users/${userId}/transition`, payload),

  // Profile
  getProfile: (userId: string) =>
    api.get<UserProfileDTO>(`/api/v1/users/${userId}/profile`),
  createProfile: (userId: string, payload: UserProfileCreateDTO) =>
    api.post<UserProfileDTO>(`/api/v1/users/${userId}/profile`, payload),
  updateProfile: (userId: string, payload: UserProfileUpdateDTO) =>
    api.patch<UserProfileDTO>(`/api/v1/users/${userId}/profile`, payload),

  // Identifiers
  listIdentifiers: (userId: string) =>
    api.get<UserIdentifierDTO[]>(`/api/v1/users/${userId}/identifiers`),
  createIdentifier: (userId: string, payload: UserIdentifierCreateDTO) =>
    api.post<UserIdentifierDTO>(
      `/api/v1/users/${userId}/identifiers`,
      payload,
    ),
  deleteIdentifier: (userId: string, identifierId: string) =>
    api.delete(`/api/v1/users/${userId}/identifiers/${identifierId}`),

  // Role assignments
  listRoleAssignments: (userId: string) =>
    api.get<RoleAssignmentDTO[]>(`/api/v1/users/${userId}/roles`),
  createRoleAssignment: (userId: string, payload: RoleAssignmentCreateDTO) =>
    api.post<RoleAssignmentDTO>(`/api/v1/users/${userId}/roles`, payload),
  deleteRoleAssignment: (userId: string, assignmentId: string) =>
    api.delete(`/api/v1/users/${userId}/roles/${assignmentId}`),

  // Platform client-users (PO bootstrap)
  listClientUsers: (clientId: string) =>
    api.get<ClientUserDTO[]>(`/api/v1/platform/clients/${clientId}/users`),
  getClientUser: (clientId: string, userId: string) =>
    api.get<ClientUserDTO>(
      `/api/v1/platform/clients/${clientId}/users/${userId}`,
    ),
  createClientUser: (clientId: string, payload: ClientUserCreateDTO) =>
    api.post<ClientUserCreateResponseDTO>(
      `/api/v1/platform/clients/${clientId}/users`,
      payload,
    ),
  updateClientUser: (
    clientId: string,
    userId: string,
    payload: ClientUserUpdateDTO,
  ) =>
    api.patch<ClientUserDTO>(
      `/api/v1/platform/clients/${clientId}/users/${userId}`,
      payload,
    ),
  transitionClientUser: (
    clientId: string,
    userId: string,
    payload: ClientUserTransitionDTO,
  ) =>
    api.post<ClientUserDTO>(
      `/api/v1/platform/clients/${clientId}/users/${userId}/transition`,
      payload,
    ),
  deleteClientUser: (clientId: string, userId: string) =>
    api.delete(`/api/v1/platform/clients/${clientId}/users/${userId}`),
};
