/**
 * Typed DTOs mirroring the C-08 configuration backend
 * (kernel/config/routes/*.py). IDs and timestamps are serialized as strings;
 * free-form value fields use `unknown` (never `any`).
 */

export type ConfigValueType = 'string' | 'number' | 'boolean' | 'json' | 'date';

export interface ConfigKeyDTO {
  id: string;
  key: string;
  type: ConfigValueType;
  default_value: unknown;
  merge_strategy: string;
  category: string;
  module: string | null;
  description: string;
  is_feature_toggle: boolean;
  is_deprecated: boolean;
  deprecated_at: string | null;
  replacement_key: string | null;
  allowed_values: unknown;
  created_at: string;
  updated_at: string;
}

export interface ConfigKeyListResponse {
  total: number;
  page: number;
  page_size: number;
  items: ConfigKeyDTO[];
}

export interface ConfigKeyCreateDTO {
  key: string;
  type: ConfigValueType;
  default_value: unknown;
  category: string;
  description: string;
  merge_strategy?: string;
  module?: string | null;
  is_feature_toggle?: boolean;
  allowed_values?: unknown;
}

export interface ConfigKeyUpdateDTO {
  default_value?: unknown;
  description?: string | null;
  merge_strategy?: string | null;
  category?: string | null;
  module?: string | null;
  is_feature_toggle?: boolean | null;
  allowed_values?: unknown;
  is_deprecated?: boolean | null;
  replacement_key?: string | null;
}

export interface ConfigValueDTO {
  id: string;
  key_id: string;
  scope_type: string; // client | institution
  scope_id: string | null;
  client_id: string | null;
  institution_id: string | null;
  value: unknown;
  created_at: string;
  updated_at: string;
  updated_by: string;
}

export interface ConfigValueListResponse {
  total: number;
  page: number;
  page_size: number;
  items: ConfigValueDTO[];
}

export interface ConfigValueCreateDTO {
  key_id: string;
  scope_type: string;
  scope_id: string;
  value: unknown;
}

export interface ConfigValueUpdateDTO {
  value: unknown;
}

export interface ConfigResolveResultDTO {
  key: string;
  resolved_value: unknown;
  source_scope: string;
}

export interface ConfigAuditDTO {
  id: string;
  key_id: string;
  scope_type: string;
  scope_id: string | null;
  action: string;
  actor_user_id: string | null;
  actor_role: string;
  timestamp: string;
}

export interface ConfigAuditListResponse {
  total: number;
  page: number;
  page_size: number;
  items: ConfigAuditDTO[];
}
