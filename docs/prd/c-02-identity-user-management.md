# PRD — C-02 Identity & User Management (User Creation & Activation)

> **Capability:** C-02 Identity & User Management (intersecting C-03 Authentication)
> **Capability layer / phase:** Kernel · Critical · Phase 1
> **Status:** Draft for impact classification → proposal/spec/design/tasks
> **Last updated:** 2026-08-03
> **Decisional source of truth:** `docs/architecture/adr-c02-identity-user-management-implementation.md` (5 locked decisions D1–D5)
> **Companion docs:** `docs/platform-capabilities/platform-capabilities-v3.md` §C-02, §C-03; `docs/architecture/architecture-v1.md`; `docs/requirements/functional-requirements.md` §1.3, §1.4; `docs/prd/client-user-bootstrap.md`; `docs/prd/c-02-impact-classification.md`
> **Scope note:** This is a **product** requirements document. It is deliberately free of implementation detail (DB column types, API shapes, RLS policy text, Casbin rule syntax). Those belong in the spec/design phase, sourced from the ADR. Decisions are referenced by ID (e.g., "per D1") rather than re-specified here.

---

## 1. Problem

The School ERP platform has two user populations — Client Directors (client-leadership tier in `client_user`) and institution users (Admin, Teacher, Student, Parent in `app_user`). Both need to be created by an authority and then activate themselves, but today they follow **two disconnected paths**:

| User type | Creator | Activation path | Status |
|-----------|---------|----------------|--------|
| Client Director | Platform Owner | Invite JWT → `/api/auth/activate` | Partially works — has invite token but blocked by `user_metadata` NameError and RLS bugs |
| Institution user | Client Director | **None** — journey flows bypass backend entirely via Supabase Admin API | Broken in production; `service_role` key exposed in browser; no audit, no lifecycle validation |

The `/api/auth/activate` endpoint already has code to handle both tables, and the invite JWT infrastructure already exists. The gap is that `POST /api/v1/users` never mints an invite token. Making these paths identical eliminates the Supabase Admin workaround, gives every user the same creation→invite→activate lifecycle, and consolidates token minting into the single `login()` endpoint (per D1, D4).

## 2. Goals & Non-goals

### 2.1 In scope — this feature owns

| Concern | Per | Notes |
|---|---|---|
| **Unified activation flow for ALL user types** | D1 | CD and institution users follow the same creation + invite + activate chain. `/api/auth/activate` handles both `client_user` and `app_user`. Lifecycle: `invited → active` for both. |
| **Invite token minting for institution users** | D1 | `POST /api/v1/users` now mints an invite JWT and returns `invite_url` alongside the user record. Mirrors the existing CD bootstrap behavior. |
| **Role assignment at creation time** | D2 | `POST /api/v1/users` accepts an optional `role_id`. When provided, the role is assigned atomically in the same transaction. `POST /api/v1/users/{id}/roles` stays for later changes. |
| **Config-driven invite URL** | D3 | Invite URL built from `app.activationBaseUrl` config key (seeded via migration), replacing the hardcoded `http://127.0.0.1:8000`. |
| **Activate returns success + client_slug (no tokens)** | D4 | Response is `{message, user_id, user_tier, client_slug}`. No JWT tokens. Frontend redirects to `{client_slug}.<host>/login`. Login is the single token-minting path. |
| **Three pre-existing bug fixes** | D5 | `user_metadata` NameError, RLS session vars never set on endpoint sessions, `app.current_user_id` never populated. Blockers for activation — must be resolved. |
| **`user_account` parent table** | D12 | Shared identity parent for both `app_user` and `client_user`. Enables `role_assignment` and `login_attempt` to reference both user types with full referential integrity. Creation flow inserts `user_account` first, then the child row with the same UUID. |

### 2.2 Out of scope — owned by other capabilities or deferred

| Concern | Owned by / Phase | Notes |
|---|---|---|
| Email delivery of invites | C-09 Notification Framework / Future | Phase 1 returns `invite_url` in API response; creator forwards out-of-band. C-09 will handle email later without changing the activation endpoint. |
| Bulk user import | C-02 / Future | The `role_id` field remains optional to support bulk import scenarios. |
| User profile management (photo, DOB, blood group) | C-02 / Existing | Already exists via `POST /api/v1/users/{id}/profile` — unchanged. |
| User identifier management (Student ID, Employee ID) | C-02 / Existing | Already exists via `POST /api/v1/users/{id}/identifiers` — unchanged. |
| OTP login, password reset, password change | C-03 / Existing | Already exist via `/api/auth/*` endpoints — unchanged. |
| Client Director self-registration | C-02 / Future | The ADR D1 unifies the PO-created path only. Self-registration (prospective client creates their own CD) is a separate future feature. |

### 2.3 Explicit non-goals for Phase 1

- No self-registration of Client Directors (out of scope for this change; separate future capability).
- No email delivery of invite links (returns invite_url in API response; creator forwards manually).
- No JWT tokens from `/api/auth/activate` (redirect to login, per D4).
- No "batch" or "bulk" user creation — single-user creation only.

## 3. Users / Personas

| Persona | Role | Actions in this feature |
|---|---|---|
| **Platform Owner** | Operator of the SaaS platform | Creates Client Directors via `POST /api/v1/platform/clients/{id}/users`. Receives invite URL and forwards to CD. Creates institutions and institution users if needed (same endpoints as CD). |
| **Client Director** | Leader of a client (school chain, trust, education group) | Creates institution users (Admin, Teacher, Student, Parent) via `POST /api/v1/users`. Picks role at creation time. Forwards invite URL to each user. |
| **New User (any type)** | Recipient of an invite | Clicks invite link, sets password on the activation page, gets redirected to login page, logs in with their new credentials. |

## 4. User Journey

### 4.1 Client Director created by Platform Owner (existing flow, now bug-fixed)

1. PO creates a Client (tenant).
2. PO calls `POST /api/v1/platform/clients/{id}/users` with CD's email, name, role=`client_director`, user_category=`Executive Leadership`.
3. Backend inserts `user_account` row, then `client_user` row in `invited` state, assigns role in `role_assignment`, mints invite JWT, returns `invite_url`. (**No Supabase Auth call** — Supabase user is created during activate, per D11.)
4. PO forwards invite URL to CD (email or out-of-band).
5. CD clicks link → enters password → calls `/api/auth/activate`.
6. Backend verifies invite JWT, transitions `invited → active`, **creates Supabase Auth user with password** (per D11), records `login_attempt`, returns `{message, user_id, user_tier="client_leadership", client_slug="greenwood"}`.
7. Frontend redirects to `greenwood.localhost:8000/login`.
8. CD logs in with email + new password → receives custom CD JWT → redirected to dashboard.

### 4.2 Institution user created by Client Director (new flow)

1. CD logs in (already active).
2. CD calls `POST /api/v1/users` with user's email, name, `user_category_id` (e.g., "Academic Staff"), `institution_id`, and optionally `role_id` (e.g., "Teacher").
3. Backend inserts `user_account` row, then `app_user` row in `invited` state, assigns role if `role_id` provided, mints invite JWT, returns `{user, invite_url}`. (**No Supabase Auth call** — Supabase user is created during activate, per D11.)
4. CD forwards invite URL to the user.
5-8. Same as 4.1 steps 5-8, with `user_tier="institution"`.

## 5. Acceptance Criteria

| ID | Criterion | Per |
|----|-----------|-----|
| AC-1 | `POST /api/v1/users` returns `invite_url` in response alongside user data | D1 |
| AC-2 | Institution users can activate via `/api/auth/activate` with a valid invite JWT | D1 |
| AC-3 | `/api/auth/activate` handles both `client_user` and `app_user` tables | D1 |
| AC-4 | Activate transitions lifecycle from `invited` to `active` for both user types | D1 |
| AC-5 | `POST /api/v1/users` accepts optional `role_id`; role assigned atomically when provided | D2 |
| AC-6 | `POST /api/v1/users` works correctly without `role_id` (role assigned later) | D2 |
| AC-7 | Invite URL is built from `app.activationBaseUrl` config key, not hardcoded | D3 |
| AC-8 | `/api/auth/activate` response includes `user_tier` and `client_slug` fields | D4 |
| AC-9 | `/api/auth/activate` does NOT return access/refresh tokens | D4 |
| AC-10 | Activate with invalid/expired invite JWT returns 400 | D1 |
| AC-11 | Activate on an already-active user returns 400 | D1 |
| AC-12 | Activate with wrong password fails gracefully (Supabase validation) | D1 |
| AC-13 | `SupabaseAuthClientImpl.update_user` accepts `user_metadata` parameter without NameError | D5 |
| AC-14 | RLS session variables (`app.is_platform_owner`, `app.current_client_id`, `app.current_user_id`) are set on endpoint sessions from TenantContext | D5 |
| AC-15 | Journey flows no longer use Supabase Admin API for user activation | D1 |

## 6. Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Breaking change on `POST /api/v1/users` response** | Downstream consumers break | Only consumer is journey-flow HTML (in-repo). Update alongside backend changes. |
| **Breaking change on `/api/auth/activate` response** | Journey flows need updating | Update `01_platform_owner.html` step 7. |
| **RLS session-var hook affects every request** | Regressions in unrelated domains | Hook uses `SET LOCAL` (transaction-scoped); comprehensive test coverage. |
| **Privacy: PO can create a CD with any email, bypassing Supabase Auth's signup verification** | Existing risk in CD bootstrap — unchanged by this feature | Audit-logged; PO is a trusted operator. |
| **Invite token accepted as auth token in middleware** | Existing behavior (D25) — unchanged | Invite tokens are NOT used for authentication; middleware explicitly skips user_id on invite tokens. |
| **`user_metadata` NameError was hidden by tests** | Tests used `conftest.py` line 142 which sets RLS to bypass; the bug never surfaced | Fix the bug AND fix the test infrastructure to match production behavior. |

## 7. Open Questions

| # | Question | Status |
|---|----------|--------|
| Q1 | Should the `pending` lifecycle state be fully removed or just bypassed in activate? | Decided — retained on state machine, bypassed in activate (per D1) |
| Q2 | Should `app.activationBaseUrl` have a default value, or fail if not configured? | Deferred to spec phase — likely default to `http://127.0.0.1:8000` for dev, require explicit setting for production |
| Q3 | Should institution users get a separate invite email template from CDs? | Deferred to C-09 (email delivery is out of scope for Phase 1) |
| Q4 | What happens to existing institution users created before this feature who never activated? | Deferred — migration will set them to `active` if they have passwords; otherwise manual remediation |
