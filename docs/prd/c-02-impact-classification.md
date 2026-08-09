# Impact Classification — C-02 Identity & User Management (User Creation & Activation)

> **Status:** Impact classification (input to prd-to-sdd phase)
> **Capability:** C-02 — Identity & User Management (intersecting C-03 Authentication, C-08 Configuration Framework, Kernel/Auth infrastructure)
> **Decisional inputs:** `docs/architecture/adr-c02-identity-user-management-implementation.md` (ADR, Final v1.0), `docs/prd/client-user-bootstrap.md` (existing two-tier PRD)
> **Verification:** `openspec list --specs` returns "No specs found" — `openspec/specs/` is empty.

---

## Classification
- Domain status: **NEW** (primary domain C-02), **EXISTING** (C-03, C-08, Kernel/Auth — touched but OpenSpec specs not yet authored for any of these)
- Delta type: **ADDED** (C-02), **MODIFIED** (C-03, Kernel/Auth), **REMOVED** (journey flows — Supabase Admin workaround)
- Cross-cutting: **YES** — affects 5 domains (C-02, C-03, C-08, Kernel/Auth, Journey Flows)
- Recommended OpenSpec domain names: `identity-user-management` (primary), `authentication` (modified), `configuration-framework` (added key), `auth-infrastructure` (bug fixes)
- Recommended OpenSpec change name: `add-c02-user-creation-activation`

## Reasoning

This change unifies the currently-disconnected user creation + activation paths into a single flow. It touches:

- **C-02 (Identity & User Management)** — new behavior on `POST /api/v1/users` (returns invite_url, accepts optional role_id). This is the primary domain and is ADDED.
- **C-03 (Authentication)** — modified behavior on `POST /api/auth/activate` (handles both client_user and app_user, response shape changes). This is MODIFIED.
- **C-08 (Configuration Framework)** — new config key `app.activationBaseUrl`. This is ADDED.
- **Kernel/Auth infrastructure** — three bug fixes spanning `supabase_client.py` (user_metadata parameter), middleware/session plumbing (RLS session variables), and the `app.current_user_id` population. These are MODIFIED.
- **Journey Flows** — the Supabase Admin workaround in `backend/static/journey_flows/02_client_director.html` (steps 7-8, 10b-10c, 12b-12c) and `09_platform_bootstrap.html` (step 9c-9d) is retired. These are REMOVED.

Since no OpenSpec specs exist yet for any of these domains, all requirement statements will be ADDED deltas within new domain spec files. MODIFIED and REMOVED items are behavioral changes to existing code, expressed as ADDED requirements in their respective domain specs (since there is no prior spec to modify).

## ADDED requirements (high-level)

### C-02 — identity-user-management

- **`user_account` parent table** — A new `user_account` table serves as the shared identity parent for both `app_user` and `client_user`. Both child tables reference `user_account.id` via FK. The `role_assignment.user_id` and `login_attempt.user_id` FKs point to `user_account.id` instead of `app_user.id`. This enables CD users to have role assignments and login audit records with full referential integrity. (ADR D12)
- **Unified invite token minting for all user types** — `POST /api/v1/users` (institution users) now mints an invite JWT and returns `{user, invite_url}` alongside the `UserDTO`. Mirrors the existing CD bootstrap behavior from `POST /api/v1/platform/clients/{id}/users`. (ADR D1)
- **Optional role_id on user creation** — `UserCreateDTO` accepts an optional `role_id` field. When provided, the role is assigned atomically in the same transaction as user creation. The existing `POST /api/v1/users/{id}/roles` endpoint is preserved for later role changes. (ADR D2)
- **Single lifecycle arc for all user types** — Both CD and institution users follow `invited → active` via `/api/auth/activate`. The `pending` state is retained on the state machine for manual transitions but removed from the normal activation flow. (ADR D1)
- **Response contract change** — `POST /api/v1/users` response changes from `UserDTO` to a combined object containing both the user and the invite URL. Breaking change for downstream consumers. (ADR D1)

### C-03 — authentication

- **Unified activation for both user tiers** — `/api/auth/activate` now handles both `client_user` and `app_user` tables. The current code already contains the branching logic (lines 355-395 of service.py); the change is that institution users now reach this endpoint (previously they had no activation path). (ADR D1)
- **Activate response shape change** — Response changes from `{message}` to `{message, user_id, user_tier, client_slug}`. The `client_slug` field enables the frontend to redirect to the correct tenant-scoped login page. No JWT tokens are returned. (ADR D4)
- **Lifecycle transition for institution users** — Activate now sets institution user lifecycle directly from `invited → active`, skipping the current `pending` intermediate. The transition endpoint retains `invited → pending → active` for manual admin flows. (ADR D1)
- **Supabase Auth user creation deferred to activate time** — Bootstrap no longer creates Supabase Auth users. The activate endpoint creates the Supabase Auth user **with password** in a single `POST /auth/v1/admin/users` call. This fixes the "User not allowed" error from `PUT /admin/users/<id>` (D11). The `SupabaseAuthClient.create_user` method gains an optional `password` parameter.

### C-08 — configuration-framework

- **New config key `app.activationBaseUrl`** — Seeded via a new Alembic migration per AGENTS.md §8. Replaces the hardcoded `http://127.0.0.1:8000` in `client_user_service.py` line 78. Value is read at runtime via `config.get("app.activationBaseUrl")`. (ADR D3)

### Kernel/Auth infrastructure (bug fixes — prerequisite)

- **Fix `SupabaseAuthClientImpl.update_user` NameError** — Add `user_metadata: dict | None = None` parameter to the implementation signature at `supabase_client.py:252`. The method body already references `user_metadata` at line 270; fixing the signature resolves the NameError. (ADR D5)
- **Add RLS session-var hook** — Implement a SQLAlchemy `before_request` event or `Session` listener that runs `SET LOCAL app.is_platform_owner`, `SET LOCAL app.current_client_id` from the resolved `TenantContext` on every endpoint session. (ADR D5)
- **Populate `app.current_user_id`** — Set `SET LOCAL app.current_user_id` in the same session hook, using `ctx.user_id` from `TenantContext`. Available for authenticated requests; NULL for unauthenticated activate (which operates with elevated privileges). (ADR D5)

## MODIFIED behavior

- **`POST /api/v1/users` response shape** — Breaking change: response changes from `UserDTO` to `{user: UserDTO, invite_url: str}`. Any downstream consumer (currently only journey-flow HTML) must be updated.
- **`POST /api/auth/activate` response shape** — Breaking change: response adds `user_tier` and `client_slug` fields. The journey-flow HTML (`01_platform_owner.html` step 7) must be updated.
- **`SupabaseAuthClientImpl.update_user` signature** — Adds `user_metadata` parameter. All callers (bootstrap_invite, activate, password_change) must be verified. No caller passes it today except bootstrap_invite (which currently fails with NameError).
- **`SupabaseAuthClientImpl.create_user` signature** — Adds optional `password` parameter. The `POST /auth/v1/admin/users` endpoint accepts `password` at creation time. Bootstrap callers omit it (no password needed); activate caller passes it. (D11)
- **Bootstrap no longer creates Supabase Auth users** — Both `CDStrategy.create_user` and `InstitutionUserStrategy.create_user` no longer call `self._supabase.create_user()`. They create only the DB row and mint the invite JWT. (D11)
- **Activate creates Supabase Auth user with password** — `AuthService.activate` calls `self._supabase.create_user(user_id, email, password=password, user_metadata={...})` after DB commit. No `update_user` call. (D11)
- **`role_assignment.user_id` FK changed** — FK target changes from `app_user.id` to `user_account.id`. CD users can now have role_assignment rows. (D12)
- **`login_attempt.user_id` FK changed** — FK target changes from `app_user.id` to `user_account.id`. CD login audit recording works. (D12)
- **User creation inserts `user_account` first** — Both CD and institution user creation flows insert a `user_account` row before the child row (`app_user` or `client_user`). The UUID is shared. (D12)

## REMOVED behavior

- **Supabase Admin workaround in journey flows** — Steps 7-8 in `02_client_director.html` (PUT auth/v1/admin/users + PATCH rest/v1/app_user for Admin), steps 10b-10c (Teacher), steps 12b-12c (Student), and steps 9c-9d in `09_platform_bootstrap.html` are replaced with backend transition endpoint calls. The `SUPABASE_SERVICE_ROLE_KEY` requirement is reduced (still needed for institution-user password setup until the invite JWT flow reaches institution users, then fully removed).
- **"Pending"state from normal activation flow** — Institution users no longer go through `pending` during activation. The state machine retains the state, and the transition endpoint retains the arc, but the activate endpoint sets `active` directly.

## Boundary relationships (NOT modifications)

| C-02 relationship | Direction | Other capability | Nature | Why it is NOT a modification to the other domain |
|---|---|---|---|---|
| User creation mints invite JWT | C-02 → C-03 | C-03 Authentication | C-02 calls `mint_invite_token()` from `kernel/auth/services/invite_token.py` | C-03 owns `mint_invite_token`; C-02 consumes it. This is a consumer relationship, not a modification of C-03. |
| Activate endpoint handles both tiers | C-03 → C-02 | C-02 Identity | C-03 reads `client_user` and `app_user` tables to look up the activating user | C-02 owns the tables; C-03 reads them. This is a read-dependency, not a modification. |
| New config key `app.activationBaseUrl` | C-02 → C-08 | C-08 Config | C-02 reads config key at runtime | C-08 owns config keys; C-02 accesses them via `config.get()`. This is a consumer relationship. |
| RLS session-var hook | Kernel → all | All domains | Middleware sets PostgreSQL session variables read by RLS policies on all tables | This is infrastructure, not domain modification. Every domain benefits from the fix. |
| role_id on UserCreateDTO affects Casbin | C-02 → C-04 | C-04 Authorization | Role assignment creates rows in `role_assignment` table | C-04 owns the authorization framework; C-02 writes to role_assignment. C-04's spec defines the schema; C-02's spec states that it writes a role_assignment row. No modification to C-04's spec. |

## Artifacts affected

| Artifact | Action |
|---|---|
| `docs/architecture/adr-c02-identity-user-management-implementation.md` | Done (this is the source document) |
| `docs/prd/c-02-impact-classification.md` | This document |
| `openspec/changes/refactor-c02-user-service-strategy-pattern/specs/identity-user-management/spec.md` | MODIFIED delta (D12: user_account parent table, CD role_assignment) |
| `openspec/changes/refactor-c02-user-service-strategy-pattern/specs/auth-infrastructure/spec.md` | MODIFIED delta (D12: user_account model, FK changes) |
| `openspec/changes/refactor-c02-user-service-strategy-pattern/specs/authentication/spec.md` | MODIFIED delta (D12: no change to activate flow, but login_attempt FK updated) |
| `openspec/changes/refactor-c02-user-service-strategy-pattern/design.md` | MODIFIED (D12: user_account schema, migration steps, creation flow) |
| `openspec/changes/refactor-c02-user-service-strategy-pattern/tasks.md` | MODIFIED (D12: new tasks for user_account model, migration, repo changes) |
| `backend/kernel/user/models/` | New `UserAccount` model; `AppUser` and `ClientUser` get FK to `UserAccount` |
| `backend/kernel/user/repos/user_repo.py` | `create()` inserts `user_account` first |
| `backend/kernel/user/repos/client_user_repo.py` | `create()` inserts `user_account` first |
| `backend/kernel/user/services/strategies/cd_strategy.py` | `create_user` inserts `role_assignment` (now works with D12 FK) |
| `backend/kernel/auth/models/login_attempt.py` | FK changes from `app_user.id` to `user_account.id` |
| `backend/kernel/user/models/role_assignment.py` | FK changes from `app_user.id` to `user_account.id` |
| `backend/migrations/versions/015_user_account_parent_table.py` | New migration — create table, backfill, FK changes |
| `backend/tests/fake_supabase_auth.py` | Code change — add `password` parameter to `create_user` |
| `backend/tests/test_c02_user.py`, `backend/tests/test_c03_auth.py` | Code change — update tests for new flow |
| `backend/kernel/auth/bootstrap.py` | Platform Owner bootstrap inserts `user_account` first |
| `backend/kernel/auth/services/service.py` | Activate flow — optional `user_account` early check |
| `backend/kernel/middleware.py` | No change (query already works with new FK target) |
