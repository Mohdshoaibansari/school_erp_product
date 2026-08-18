/**
 * Typed DTOs mirroring the C-02 identity-user backend
 * (kernel/user/services/dtos.py) — person-model revamp (T-28).
 */

export interface PersonCreateDTO {
  name: string;
  date_of_birth?: string | null;
  gender?: string | null;
  blood_group?: string | null;
  photo?: string | null;
  contact_phone?: string | null;
  contact_email?: string | null;
  demographics?: Record<string, unknown> | null;
}

export interface PersonDTO {
  id: string;
  client_id: string;
  name: string;
  date_of_birth: string | null;
  gender: string | null;
  blood_group: string | null;
  photo: string | null;
  contact_phone: string | null;
  contact_email: string | null;
  demographics: Record<string, unknown> | null;
  status: string;
  is_minor: boolean | null;
  is_verified: boolean | null;
  created_at: string;
  updated_at: string;
}

export interface UserCreateDTO {
  email: string;
  person_data: PersonCreateDTO;
  institution_id: string;
  role_id: string | null;
}

export interface UserUpdateDTO {
  name?: string | null;
  email?: string | null;
  lifecycle_status?: string | null;
}

export interface UserDTO {
  id: string;
  client_id: string;
  institution_id: string | null;
  email: string;
  person: PersonDTO;
  lifecycle_status: string;
  created_at: string;
  updated_at: string;
}

export interface UserCreateResponseDTO {
  user: UserDTO;
  invite_url: string;
}

export interface RoleAssignmentCreateDTO {
  role_id: string;
  scope: string | null;
}

export interface RoleAssignmentDTO {
  id: string;
  client_id: string;
  user_id: string;
  role_id: string;
  scope: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserIdentifierCreateDTO {
  type: string;
  value: string;
}

export interface UserIdentifierDTO {
  id: string;
  client_id: string;
  user_id: string;
  type: string;
  value: string;
  created_at: string;
  updated_at: string;
}

export interface UserLifecycleTransitionDTO {
  new_state: string | null;
  reason: string | null;
}

/** Client-user (client director bootstrap) DTOs — platform client-users routes. */
export interface ClientUserCreateDTO {
  email: string;
  person_data: PersonCreateDTO;
  role_id: string;
  client_id: string | null;
}

export interface ClientUserUpdateDTO {
  name?: string | null;
  email?: string | null;
}

export interface ClientUserDTO {
  id: string;
  client_id: string;
  email: string;
  person: PersonDTO;
  role_id: string;
  lifecycle_status: string;
  created_at: string;
  updated_at: string;
}

export interface ClientUserTransitionDTO {
  new_state: string;
  reason: string | null;
}

export interface ClientUserCreateResponseDTO {
  user_id: string;
  email: string;
  invite_url: string;
  client_id: string;
  user: UserDTO;
}
