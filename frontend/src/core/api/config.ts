import { api } from './client';
import type {
  ConfigAuditListResponse,
  ConfigKeyDTO,
  ConfigKeyListResponse,
  ConfigResolveResultDTO,
  ConfigValueCreateDTO,
  ConfigValueDTO,
  ConfigValueListResponse,
  ConfigValueUpdateDTO,
} from './dto/config';

export const configApi = {
  // Keys
  listKeys: (filters?: {
    key?: string;
    category?: string;
    module?: string;
    include_deprecated?: boolean;
    page_size?: number;
  }) =>
    api.get<ConfigKeyListResponse>('/api/v1/config/keys', {
      params: filters ?? {},
    }),
  getKey: (keyId: string) =>
    api.get<ConfigKeyDTO>(`/api/v1/config/keys/${keyId}`),

  // Values (scoped overrides)
  listValues: (filters?: {
    key_id?: string;
    scope_type?: string;
    scope_id?: string;
    page_size?: number;
  }) =>
    api.get<ConfigValueListResponse>('/api/v1/config/values', {
      params: filters ?? {},
    }),
  getValue: (valueId: string) =>
    api.get<ConfigValueDTO>(`/api/v1/config/values/${valueId}`),
  createValue: (payload: ConfigValueCreateDTO) =>
    api.post<ConfigValueDTO>('/api/v1/config/values', payload),
  updateValue: (valueId: string, payload: ConfigValueUpdateDTO) =>
    api.patch<ConfigValueDTO>(`/api/v1/config/values/${valueId}`, payload),
  deleteValue: (valueId: string) =>
    api.delete(`/api/v1/config/values/${valueId}`),

  // Resolve (effective value + source scope)
  resolveKey: (keyName: string, params?: {
    institution_id?: string | null;
    client_id?: string | null;
  }) =>
    api.get<ConfigResolveResultDTO>(
      `/api/v1/config/resolve/${encodeURIComponent(keyName)}`,
      { params: params ?? {} },
    ),

  // Audit
  listAudit: (filters?: {
    key_id?: string;
    action?: string;
    page_size?: number;
  }) =>
    api.get<ConfigAuditListResponse>('/api/v1/config/audit', {
      params: filters ?? {},
    }),
};
