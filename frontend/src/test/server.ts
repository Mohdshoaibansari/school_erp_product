import { setupServer } from 'msw/node';

/**
 * Shared MSW server. Tests import this instance and register per-test handlers
 * via `server.use(...)`. Lifecycle (listen/reset/close) is wired in
 * `setupTests.ts`.
 */
export const server = setupServer();
