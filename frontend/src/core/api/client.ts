import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { normalizeApiError } from './errors';
import {
  readAccessToken,
  readRefreshToken,
  writeTokens,
  clearTokens,
  sessionEvents,
} from './tokenStore';

type RetriableRequestConfig = InternalAxiosRequestConfig & { __retried?: boolean };

const REFRESH_URL = '/api/auth/refresh';

/** A single-flight queued silent refresh so N concurrent 401s trigger one refresh. */
let refreshPromise: Promise<string | null> | null = null;

function isAuthUrl(url: string | undefined): boolean {
  return !!url && url.includes('/api/auth/');
}

async function doRefresh(): Promise<string | null> {
  const refreshToken = readRefreshToken();
  if (!refreshToken) return null;

  // Bare axios (no interceptors) to avoid recursion. The refresh endpoint does
  // not require a bearer token — it authenticates via the refresh token body.
  const response = await axios.post<{ access_token: string; refresh_token: string }>(
    REFRESH_URL,
    { refresh_token: refreshToken },
    { baseURL: '' },
  );

  writeTokens(response.data.access_token, response.data.refresh_token);
  return response.data.access_token;
}

function queueRefresh(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = doRefresh().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

export const api = axios.create({ baseURL: '' });

api.interceptors.request.use((config) => {
  const token = readAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (!axios.isAxiosError(error)) {
      return Promise.reject(normalizeApiError(error));
    }

    const { response, config } = error;
    const status = response?.status ?? 0;
    const url = config?.url ?? '';
    const retriable = (config ?? {}) as RetriableRequestConfig;

    // 401 handling -------------------------------------------------------
    if (status === 401) {
      // Never refresh-loop on auth routes (including the refresh route itself).
      if (isAuthUrl(url)) {
        if (url.includes('/refresh')) {
          clearTokens();
          sessionEvents.onExpired();
        }
        return Promise.reject(normalizeApiError(error));
      }

      if (retriable.__retried) {
        clearTokens();
        sessionEvents.onExpired();
        return Promise.reject(normalizeApiError(error));
      }

      try {
        const newToken = await queueRefresh();
        if (!newToken) {
          clearTokens();
          sessionEvents.onExpired();
          return Promise.reject(normalizeApiError(error));
        }
        retriable.__retried = true;
        retriable.headers.Authorization = `Bearer ${newToken}`;
        return api(retriable);
      } catch {
        clearTokens();
        sessionEvents.onExpired();
        return Promise.reject(normalizeApiError(error));
      }
    }

    // 403 handling -------------------------------------------------------
    // No redirect. Normalize with the `forbidden` flag so callers render the
    // friendly permission-denied surface (R8, REQ-SHELL-07).
    if (status === 403) {
      return Promise.reject(normalizeApiError(error));
    }

    return Promise.reject(normalizeApiError(error));
  },
);

export type { AxiosError };
