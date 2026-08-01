## Why

The School ERP platform models users in a single `app_user` table, conflating **client-leadership users** (a Client Director who manages a whole chain, no `institution_id`) with **institution-scoped users** (Admin, Teacher, Student, Parent inside one school). This friction surfaced concretely during C-08 journey-flow testing:

- The bootstrap failure — Platform Owner (PO) creates a client but cannot call `POST /api/v1/users` to appoint its first Client Director (PO has no `client_id` in their JWT), forcing the documented workaround of direct Supabase REST API inserts with `service_role` (no audit logging, no validation, exposed admin key).
- The RLS bypass failure — even the Supabase-direct workaround fails on the cloud DB because `app_user` RLS policies depend on PostgreSQL session variables (`app.is_platform_owner`, `app.current_client_id`) that ONLY our middleware sets (the workaround returns `42501 permission denied for table app_user`).
- The visibility tension — PO must "create a client user" (provision a tenant) WITHOUT "gaining access to client data" (students, teachers, grades, fees). The single-table model makes these hard to separate.

This change resolves all three by introducing a **two-tier user model**: the PO provisions Client Directors through audit-logged backend endpoints into a new `client_user` table, while RLS on existing institution tables stays the hard wall keeping the PO out of tenant data. Per PRD `docs/prd/client-user-bootstrap.md` (D1–D14, locked 2026-08-01).

## What Changes

- **NEW capability `client-user-bootstrap`** — Introduces the `client_user` table (mirrors `app_user` columns + `role_id` column + `client_id`, no `institution_id`) and a parallel `client_user_lifecycle_event` table (D1, D3, D10). Grants the PO a new endpoint surface `POST /api/v1/platform/clients/$ID/users` (bootstrap), `GET` (list), `PATCH` (suspend), `DELETE` (revoke) protected by `require_platform_owner` (D4).

- **NEW bootstrap invite flow (reuse C-03)** — `POST /api/v1/platform/clients/$ID/users` body `{email, name, role}` creates a Supabase Auth user in `invited` state with NO password, stamps `user_metadata.user_tier = "client_leadership"`, inserts the `client_user` row with `lifecycle_status='invited'`, mints an invite JWT via the existing `kernel/auth/services/invite_token.py`, and returns the invite URL in the response (PO forwards it out-of-band — no SMTP infra) (D6, D7).

- **MODIFIED login flow (D2, D9)** — `/api/auth/login` reads `user_metadata.user_tier` from Supabase Auth: `"client_leadership"` → queries `client_user` and mints a custom HS256 JWT carrying `{sub, user_tier, client_id, role_id, exp}` (no `institution_id`); `"institution"` → queries `app_user` as before. Strict-fail for users without the flag — D14 greenfield approach (delete existing Supabase Auth users except `admin@school-erp.com`).

- **MODIFIED middleware (D9)** — Reads `user_tier` claim from the JWT and sets `app.current_client_id` from `client_id` for client-leadership tokens. No DB lookup per request.

- **MODIFIED Casbin policy loader (D3)** — Adds `client_user.role_id` as a SECOND source of client-leadership-role mappings alongside the existing `role_assignment` source for institution roles.

- **NEW `client_user` RLS (D5, D8)** — PO CRUD on all rows; CD SELECT/UPDATE on own row only (`id = current_user_id()`); CD INSERT/DELETE/sibling-list blocked. Existing RLS on `app_user`, `institution`, `fees`, `homework` stays AS-IS — PO lacks `app.current_client_id` so institution rows filter to ZERO (defense-in-depth: `require_permission` PO bypass stays, RLS is the wall).

- **NEW Alembic migration 011** — Creates `client_user` + `client_user_lifecycle_event`. Moves any existing `app_user` rows with `institution_id IS NULL` into `client_user`. Backfills `user_metadata.user_tier` on those users via Supabase Admin API (D13, D14).

- **NEW Alembic migration 012 — BREAKING** — `ALTER TABLE app_user ALTER COLUMN institution_id SET NOT NULL`. Safe because migration 011 cleared NULL rows. Also tightens `UserCreateDTO.institution_id` to required at the API layer (D13).

- **REMOVED behavior (D13)** — Migration 008's rationale ("`app_user.institution_id` is nullable to support client-leadership users without an institution") is reversed. Documented as a REMOVED requirement in the tenant-institution delta spec.

- **REMOVED bootstrap workaround** — Direct Supabase REST calls to `/rest/v1/app_user` and `/rest/v1/role_assignment` are REMOVED from the documented journey; replaced by `POST /api/v1/platform/clients/$ID/users`.

- **MODIFIED `platform-owner-followups` responsibilities** — PO gains new behavioral contract: bootstrap CDs (via invite), list CDs in any client, suspend CDs, revoke CDs.

- **MODIFIED C-08 (`configuration`) — light touch** — The existing `auth.jwtExpirySeconds` config key now ALSO serves as the natural-expiry safety net for suspended-CD JWT replay (per D12). No key semantics change.

## Capabilities

### New Capabilities
- `client-user-bootstrap`: Two-tier user model — `client_user` table (client-leadership users) parallel to `app_user` (institution-scoped users). PO provisions, lists, suspends, revokes Client Directors through `/api/v1/platform/clients/$ID/users/*`. Bootstrap via invite flow (D6, D7). CD login uses custom HS256 JWT (D9). Defense-in-depth RLS keeps PO from institution data (D8).

### Modified Capabilities
- `tenant-institution`: PO bootstrap journey switches from direct Supabase REST calls to `POST /api/v1/platform/clients/$ID/users`. Client gains a one-to-many relationship with `client_user`. **REMOVED**: `app_user.institution_id` nullable (migration 008 behavior — reversed by migration 012, BREAKING).
- `platform-owner-separation`: PO's behavioral reach extends to the NEW `client_user` table (PO CRUD). `require_platform_owner` dependency extended to protect `/api/v1/platform/clients/$ID/users/*`. Existing PO separation decisions (D2, D3, D5, D28) stay unchanged.
- `platform-owner-followups`: PO gains new behavioral responsibilities: bootstrap CDs through invite, list CDs, suspend CDs, revoke CDs. Documented as ADDED requirements in the delta spec.
- `configuration` (C-08): ADDED requirement — `auth.jwtExpirySeconds` serves double-duty as the natural-expiry safety net for suspended-CD HS256 JWTs (per D12). Key itself unchanged.

## Impact

**Affected code:**
- `backend/kernel/user/` — new `client_user` model + repo + service + DTOs; existing `UserCreateDTO` tightened to require `institution_id`.
- `backend/kernel/auth/services/service.py` — login flow branches on `user_metadata.user_tier`; mints custom HS256 JWT for CDs.
- `backend/kernel/auth/services/invite_token.py` — reused (no change to its public API).
- `backend/kernel/middleware.py` — reads `user_tier` claim, sets `app.current_client_id` from `client_id` for client-leadership tokens.
- `backend/kernel/authz/services/policy_loader.py` — extended to load `client_user.role_id` mappings as a second source (D3).
- `backend/business/tenant_institution/routes/platform.py` — gains nested `/clients/$ID/users` router.
- `backend/kernel/authz/dependencies.py` — `require_platform_owner` extended to new endpoints.
- `backend/config.py` — `/api/v1/platform/clients/` already in `PLATFORM_PATHS`; nested `/api/v1/platform/clients/$ID/users/*` inherits the whitelist (no change likely; verify).

**Affected DB / migrations:**
- `migrations/versions/011_client_user_bootstrap.py` (NEW)
- `migrations/versions/012_app_user_institution_id_not_null.py` (NEW, BREAKING)
- `migrations/versions/008_nullable_institution_id.py` rationale reversed (no migration change; spec doctrine change).

**Affected APIs:**
- NEW: `/api/v1/platform/clients/{client_id}/users` (POST, GET) and `/api/v1/platform/clients/{client_id}/users/{user_id}` (PATCH, DELETE).
- MODIFIED: `/api/auth/login` — branch on `user_metadata.user_tier` (response tokens carry new `user_tier` and `client_id` claims for CDs).
- MODIFIED: `POST /api/v1/users` — `institution_id` becomes required (D13 BREAKING).

**Dependencies:**
- Reuses C-03 `kernel/auth/services/invite_token.py` (no new dep).
- Reuses C-04 `require_platform_owner` dependency (no new dep).
- Reuses C-08 `auth.jwtExpirySeconds` for suspended-CD JWT TTL safety (D12, light touch).
- Requires a one-shot operational greenfield wipe of Supabase Auth users (except PO `admin@school-erp.com`) — documented in tasks, not a code migration.

**Systems:**
- Supabase Auth — every user row gets `user_metadata.user_tier` stamped (via Supabase Admin API during creation and migration 011 backfill).
- PostgreSQL — two migrations; new RLS policy on `client_user`; existing RLS unchanged on institution tables.
- Frontend journey flows — `01_platform_owner.html` Steps 6–8 will be replaced with a single call to `POST /api/v1/platform/clients/$ID/users`. (UI rewrite tracked separately; not required for spec approval.)