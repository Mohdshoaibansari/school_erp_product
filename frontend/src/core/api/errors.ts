import axios from 'axios';

/**
 * Normalized API error surfaced to the UI. A single consistent shape for
 * toasts, inline alerts, and the friendly 403 surface (REQ-SHELL-07).
 */
export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;
  readonly forbidden: boolean;

  constructor(
    status: number,
    message: string,
    opts: { code?: string; forbidden?: boolean } = {},
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = opts.code;
    this.forbidden = opts.forbidden ?? false;
  }
}

function detailToMessage(detail: unknown, fallback: string): string {
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object') {
    const record = detail as Record<string, unknown>;
    if (typeof record.message === 'string') return record.message;
    if (typeof record.error === 'string') return record.error;
    if (typeof record.detail === 'string') return record.detail;
    try {
      return JSON.stringify(record);
    } catch {
      return fallback;
    }
  }
  return fallback;
}

function detailToCode(detail: unknown): string | undefined {
  if (detail && typeof detail === 'object') {
    const record = detail as Record<string, unknown>;
    if (typeof record.error === 'string') return record.error;
  }
  return undefined;
}

/**
 * Normalize an arbitrary rejection (usually an AxiosError from the API client)
 * into a consistent `ApiError`. A 403 response sets `forbidden === true`.
 */
export function normalizeApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;

  if (axios.isAxiosError(error)) {
    const status = error.response?.status ?? 0;
    const data = error.response?.data as unknown;
    const detail =
      data && typeof data === 'object'
        ? (data as { detail?: unknown }).detail
        : undefined;
    return new ApiError(status, detailToMessage(detail, error.message), {
      code: detailToCode(detail),
      forbidden: status === 403,
    });
  }

  if (error instanceof Error) {
    return new ApiError(0, error.message);
  }

  return new ApiError(0, 'An unexpected error occurred');
}

/** Type guard for the friendly 403 surface. */
export function isForbidden(error: unknown): boolean {
  return error instanceof ApiError && error.forbidden;
}
