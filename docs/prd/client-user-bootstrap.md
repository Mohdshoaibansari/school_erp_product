# PRD — Client User Bootstrap & Tier Separation

> **Capability:** Client User Bootstrap (two-tier user model)
> **Capability layer / phase:** Kernel · Critical · Phase 1
> **Status:** Draft for impact classification → proposal/spec/design/tasks
> **Last updated:** 2026-08-01
> **Decisional source of truth:** This PRD. All 14 decisions (D1–D14) were locked in a grill-me session on 2026-08-01.
> **Companion docs:** `docs/specs/platform-owner-separation.md` (PO-as-Auth-only history → D11 lock); `docs/prd/c-01-tenant-institution.md` (current PO client-creation flow); `docs/prd/c-08-configuration-framework.md` (PRD format template); `docs/architecture/architecture-v1.md`; `docs/architecture/adr-platform-software-architecture.md`
> **Scope note:** This is a **product** requirements document. It is deliberately free of implementation detail (DB column types, API request/response shapes, RLS policy SQL, Casbin rule syntax). Those belong in the spec/design phase, sourced from this PRD. Decisions are referenced by ID (e.g., "per D1") rather than re-specified in implementation.

---

## 1. Problem

The School ERP platform models users in a single `app_user` table. That table must serve two structurally different populations:

1. **Client-leadership users** — the Client Director (and future Client Admins, Billing Contacts) who manage an entire client (a school chain) and have NO institution. Their `institution_id` is `NULL`.
2. **Institution-scoped users** — Admin, Teacher, Student, Parent inside one specific school. Their `institution_id` is the school they belong to.

Co-locating both populations in one table created a recurring tension that surfaced during C-08 journey-flow testing:

- **The bootstrap problem.** When a Platform Owner (PO) creates a new client, they must also create the first Client Director for that client. The PO has no `client_id` in their JWT (by D5 of the Platform-Owner-Separation spec) and so cannot call `POST /api/v1/users` — that endpoint requires a tenant context. Today the journey-flow UI works around this by calling the Supabase REST API directly with the `service_role` key to insert `app_user` and `role_assignment` rows. That workaround bypasses our backend entirely: no audit logging, no service-layer validation, no lifecycle gating, and it exposes the `service_role` key in the browser.
- **The RLS bypass failure.** Even the Supabase-direct workaround fails on the cloud DB. The `app_user` INSERT RLS policy requires `is_platform_owner() OR client_id = current_client_id()`, where both functions read PostgreSQL session variables (`app.is_platform_owner`, `app.current_client_id`) that ONLY our middleware sets. Calls to PostgREST never set those variables, so the insert is rejected with `42501 permission denied for table app_user`. There is no clean fix on the current single-table model that does not also grant the PO read access to institution rows — which violates the core invariant.
- **The visibility tension.** The PO needs to "create a client user" (provision a tenant) without "seeing client data" (students, teachers, grades, fees). On the single-table model these two acts are hard to separate — both touch `app_user`, both touch RLS, and the existing `is_platform_owner() OR client_id = ...` clause in `app_user` RLS policies lets the PO read every institution user across every tenant whenever they go through the middleware.

The root cause is that the single-table model conflates **client-leadership provisioning** (a platform-level act) with **institution user management** (a tenant-scoped act). Splitting them across two physical tables is the only way to give the PO the first capability while cleanly walling off the second.

This feature introduces a **two-tier user model** to resolve the tension. The new `client_user` table holds all client-leadership-scope users; `app_user` becomes institution-only. The PO provisions Client Directors through audit-logged backend endpoints, and RLS on institution tables remains the hard wall that keeps the PO out of tenant data.

---

## 2. Goals & Non-goals

### 2.1 In scope — this feature owns

| Concern | Per | Notes |
|---|---|---|
| **Two-tier user model** (`client_user` + `app_user` separation) | D1 | New `client_user` table holds all client-leadership-scope users (first Client Director + future Client Admins + Billing Contacts). `app_user` becomes institution-only — every row has a non-null `institution_id` (per D13). |
| **Login lookup by `user_metadata.user_tier`** | D2 | Supabase Auth user_metadata carries `user_tier` flag ("client_leadership" \| "institution"). Login reads the flag and queries the correct table. Explicit coupling with Supabase Auth — every user-creation path stamps the flag at creation. |
| **Role stored as a column on `client_user`** | D3 | `role_id` FK to the existing `role` table, stored directly on `client_user`. No separate `client_role_assignment` table. Casbin policy loader adds a second source (reads `client_user` for client-leadership roles, `role_assignment` for institution roles). |
| **PO endpoint surface** (`/api/v1/platform/clients/$ID/users/*`) | D4 | Nested under platform client namespace: POST (bootstrap), GET (list CDs in client), PATCH (transition/suspend), DELETE (revoke). PO uses `require_platform_owner`, NOT `require_permission`. |
| **CD access on `client_user` (own row only)** | D5 | Client Director can SELECT and UPDATE only their own row (e.g., update display name). Cannot read sibling CDs, cannot list, cannot insert/delete. RLS: `SELECT/UPDATE WHERE id = current_user_id()`. Insert/Delete/sibling-list are PO-only. |
| **Bootstrap = invite flow (no initial password)** | D6 | PO's bootstrap endpoint receives email (+name, +role), creates the Supabase Auth user in `invited` state with NO password, inserts `client_user` with `lifecycle_status='invited'`, mints an invite JWT. Reuses the existing C-03 invite infrastructure (`kernel/auth/services/invite_token.py`). CD clicks the invite link, sets their own password, lifecycle transitions invited → active. |
| **Invite URL returned in API response** | D7 | Backend returns the invite URL in the POST response; PO forwards it out-of-band (Slack, WhatsApp, phone). No SMTP infra required — matches the throwaway-test-frontend context. PO can see the link but it is single-use + short-lived. |
| **Defense-in-depth kept** (PO bypass stays, RLS is the wall) | D8 | `require_permission` PO bypass stays (D28 of Platform-Owner-Separation). RLS on tenant tables is the actual wall — PO lacks the `app.current_client_id` session var so tenant rows filter out. Existing RLS policies on `app_user` / `institution` / `fees` / `homework` stay AS-IS. The NEW `client_user` table has its own RLS allowing PO CRUD + CD own-row management. |
| **Custom HS256 JWT for CD login** | D9 | CD login mints a custom HS256 JWT (extends today's PO JWT pattern) carrying `{sub, user_tier='client_leadership', client_id, role_id, exp}`. Middleware reads claims directly, zero DB lookup per request. NO `institution_id` claim — a CD manages all institutions under their client. |
| **`client_user` mirrors `app_user` (columns + event table)** | D10 | Same columns (email, name, user_category_id, lifecycle_status, created_at, etc.) PLUS a parallel `client_user_lifecycle_event` table + state machine. Records every transition (`invited → active → suspended → archived`) with actor, reason, timestamp. PO drives CD transitions; the CD does NOT drive their own lifecycle. |
| **`app_user.institution_id` becomes NOT NULL** | D13 | Two-migration rollout: migration 011 creates `client_user`, moves any `app_user` rows with `institution_id IS NULL` into `client_user`, backfills `user_metadata.user_tier`; migration 012 ALTERs `app_user.institution_id` to NOT NULL and tightens `UserCreateDTO` to make `institution_id` required at the API layer. |
| **Strict-fail login for users without `user_tier`** | D14 | Greenfield approach — delete existing Supabase Auth users (except the PO `admin@school-erp.com`) before go-live. After the wipe, every user is created through our backend (which sets `user_tier` at creation). Login reads the flag strictly: no flag → reject with "Account requires reconfiguration." No self-heal fallback logic. |

### 2.2 Out of scope — owned by other capabilities or deferred

| Concern | Owned by / Phase | Per | Notes |
|---|---|---|---|
| **PO moves to a `platform_user` tier table** | Out — platform stays Auth-only | D11 | PO stays as today: Supabase Auth only, `user_metadata.is_platform_owner = true`, no `app_user` or `client_user` row. The new tier model is for CD + institution users only. |
| **CD token revocation on suspend** | Future (security review) | D12 | When PO suspends a CD, the suspended CD's currently-issued HS256 JWT keeps working until natural expiry. No revocation list today. Mitigation: rely on short HS256 JWT TTL (existing `auth.jwtExpirySeconds` default 3600s from C-08). Revisit at production security review. |
| **Email delivery of invites** | Future (when SMTP infra exists) | D7 | Phase 1 returns the invite URL in the API response and the PO forwards it manually. A future SMTP-backed email-delivery flow can replace this without changing the bootstrap endpoint shape. |
| **Self-registration of Client Directors** | Out — non-goal | D6 | Only the PO can bootstrap a Client Director. CDs cannot sign themselves up; they must be invited. |
| **PO read access to institution rows** (students, teachers, fees, homework) | Out — non-goal & explicit invariant | D8, D2 | The whole point of the tier split. PO must NOT gain read or write access to institution-scoped tables. RLS stays the hard wall. |
| **Institution Admin migrating to a new role** | C-02 / future | — | The Institution Admin's role definitions are owned by C-02 & C-04. This feature does NOT redefine IA's permissions; it only removes the (today-unused-on-cloud) constraint that blocked CDs from coexisting with IAs. |
| **OAuth / SSO login flows** | Future (C-03 Phase 2) | — | Only the email-password + invite flow is affected by this feature. SSO is later. |
| **Multi-CD governance** (multiple CDs per client, voting, etc.) | Future | D3 | Multiple CDs are technically supported by the model (each is a row in `client_user` with role=client_director), but no governance / voting / "primary CD" semantics are built. |

### 2.3 Explicit non-goals for Phase 1

- No PO move to a tier table (per D11).
- No token revocation (per D12).
- No email delivery (per D7).
- No self-registration (per D6).
- No PO read access to institution rows (per D8 — core invariant).
- No self-heal legacy-user fallback (per D14 — strict-fail by design).

---

## 3. Users / Personas

The feature has five actors. Precise role definitions and Casbin encoding are owned by C-04; this section only defines what each persona can do against the new `client_user` entity and the modified `app_user` invariant.

| Persona | Who they are | Scope | Reach on this feature |
|---|---|---|---|
| **Platform Owner** (PO) | The SaaS provider operating the platform. | All tenants + the platform itself. | CRUD on `client_user` across all clients via `/api/v1/platform/clients/$ID/users`. Bootstraps the first CD of any client via invite. Suspends / revokes CDs. CANNOT read or write any row in `app_user`, `institution`, `homework`, `fees` — RLS walls these off (per D8). |
| **Client Director** (CD) | The client's top administrator (trust director, chain owner). | Own client only — all institutions under it. | SELECT/UPDATE on their OWN row in `client_user` (e.g., update display name). Reads own profile. CANNOT read sibling CDs, list CDs, insert, or delete. Drives all institution-user management through the EXISTING `POST /api/v1/users` endpoint (which writes to `app_user`). |
| **Institution Admin** (IA) | The institution's in-building administrator (Principal, Vice-Principal). | Own institution only. | Unchanged from today. Creates teachers / students inside their institution via `POST /api/v1/users`. With D13, every user they create MUST have an `institution_id` (no longer optional). |
| **Teacher / Student / Parent** | Institution end-users. | Own institution. | Unchanged from today. Live in `app_user` (now strictly institution-scoped). |
| **Module Developer** (technical persona) | Engineer building a business module. | Code-level integration. | Unaffected directly. If a module needs to know whether a user is client-leadership or institution-scoped, it reads the `user_tier` from the JWT (D9) — no DB query needed. |

All writes are audited via the existing `kernel/audit.py` infrastructure with actor identity. Extra forensic events are recorded in the new `client_user_lifecycle_event` table (per D10).

---

## 4. User Journeys

### 4.1 PO bootstraps the first Client Director

1. PO logs in (existing flow) → receives a PO JWT with `is_platform_owner: true`.
2. PO creates a client via `POST /api/v1/platform/clients` (existing endpoint, unchanged).
3. PO activates the client via the existing lifecycle transition endpoint.
4. PO calls `POST /api/v1/platform/clients/$ID/users` with `{email, name, role: "client_director", ...}` (D4, D6).
5. Backend:
   - Creates a Supabase Auth user in the `invited` state with NO password.
   - Stamps `user_metadata.user_tier = "client_leadership"` on the new Auth user (D2).
   - Inserts a row into `client_user` with `lifecycle_status = "invited"`, `role_id` resolved from the role name, `client_id = $ID`.
   - Mints an invite JWT using the existing `kernel/auth/services/invite_token.py` (D6).
   - Returns the response containing the invite URL (D7).
   - Records an audit event AND a row in `client_user_lifecycle_event` (state: `invited`) (D10).
6. PO forwards the invite URL to the future CD out-of-band (Slack, WhatsApp, phone).

### 4.2 Client Director activates via invite

1. CD receives the invite URL from the PO out-of-band.
2. CD clicks the link → lands on a "set your password" page.
3. CD submits a password → backend verifies the invite JWT (existing `verify_invite_token`), sets the password on the Supabase Auth user, transitions `client_user.lifecycle_status` from `invited` to `active` (D6, D10).
4. Forensic event recorded in `client_user_lifecycle_event` (state: `active`, actor: the CD themselves completing the invite).

### 4.3 Client Director logs in

1. CD submits email + password to `POST /api/auth/login` (existing endpoint, modified flow per D2, D9).
2. Backend:
   - Verifies credentials with Supabase Auth.
   - Reads `user_metadata.user_tier` from the Supabase response.
   - Since `user_tier = "client_leadership"`, looks up the user in `client_user` (instead of `app_user`).
   - Validates `lifecycle_status = "active"`.
   - Mints a custom HS256 JWT carrying `{sub, user_tier, client_id, role_id, exp}` (D9).
   - Returns the JWT.
3. Middleware on subsequent requests reads claims directly from the JWT — zero DB lookup per request (D9). `app.current_client_id` is set from the JWT's `client_id`.

### 4.4 CD manages own profile

1. CD calls `GET /api/v1/platform/clients/$ID/users/$SELF_ID` (or a dedicated profile endpoint) → backend returns the CD's own row only (RLS: `id = current_user_id()` per D5).
2. CD calls `PATCH /api/v1/platform/clients/$ID/users/$SELF_ID` with `{name: "New Name"}` → backend updates only the own row.
3. CD cannot list, insert, or delete — RLS blocks at the database level (D5).

### 4.5 PO suspends a CD

1. PO calls `PATCH /api/v1/platform/clients/$ID/users/$UID` with `{new_state: "suspended", reason: "..."}` (D4).
2. Backend transitions `client_user.lifecycle_status` from `active` to `suspended`, records a `client_user_lifecycle_event` row (state: `suspended`, actor: PO, reason captured) (D10).
3. The CD's currently-issued HS256 JWT keeps working until natural expiry (D12). Next login attempt by the CD will be rejected because `lifecycle_status != "active"`.

### 4.6 Institution Admin creates a teacher (existing flow, tightened)

1. CD creates an Institution Admin through the existing `POST /api/v1/users` (existing endpoint). Per D13, the `UserCreateDTO` now REQUIRES `institution_id` — no longer optional.
2. IA logs in (institution-scoped JWT with both `client_id` and `institution_id`).
3. IA creates a Teacher via `POST /api/v1/users` — same as today, but `institution_id` is mandatory.

---

## 5. Acceptance Criteria

Acceptance criteria are mapped to the locked decisions. Each AC is a testable assertion the implementation MUST satisfy.

### AC-1 — Two-tier physical separation (D1, D13)
- A NEW `client_user` table exists and holds client-leadership-scope users only.
- After migration 012, `app_user.institution_id` is NOT NULL — Postgres rejects any INSERT that omits it.
- No row in `client_user` has an `institution_id` column; no row in `app_user` has a NULL `institution_id`.

### AC-2 — Login lookup by `user_tier` (D2, D9)
- A Supabase Auth user with `user_metadata.user_tier = "client_leadership"` resolves to a row in `client_user` at login.
- A Supabase Auth user with `user_metadata.user_tier = "institution"` resolves to a row in `app_user` at login.
- A CD login mints a custom HS256 JWT carrying `{sub, user_tier, client_id, role_id, exp}` (no `institution_id`).
- Middleware reads `client_id` from the JWT on subsequent requests and sets `app.current_client_id` accordingly.

### AC-3 — PO bootstrap of Client Director (D4, D6, D7)
- `POST /api/v1/platform/clients/$ID/users` with `{email, name, role}` creates a Supabase Auth user in the `invited` state, inserts a `client_user` row with `lifecycle_status = "invited"`, and returns the invite URL.
- The endpoint requires `require_platform_owner` — a non-PO token is rejected.
- The endpoint requires NO `Host` header (PO is client-independent in their own session).
- An audit event AND a `client_user_lifecycle_event` row are recorded for the bootstrap.

### AC-4 — PO list / suspend / revoke CDs (D4)
- `GET /api/v1/platform/clients/$ID/users` returns all CDs in client `$ID`. Requires `require_platform_owner`.
- `PATCH /api/v1/platform/clients/$ID/users/$UID` with `{new_state, reason}` transitions the CD's lifecycle and records a `client_user_lifecycle_event` row.
- `DELETE /api/v1/platform/clients/$ID/users/$UID` revokes the CD (archived state, rotates their Auth user to blocked, etc. per the eventual spec).

### AC-5 — CD own-row access only (D5)
- A CD calling `GET /api/v1/platform/clients/$ID/users` (list) is rejected by RLS (PO-only operation).
- A CD calling `GET /api/v1/platform/clients/$ID/users/$SELF_ID` succeeds (own row).
- A CD calling `GET /api/v1/platform/clients/$ID/users/$SIBLING_ID` is rejected by RLS (`id != current_user_id()`).
- A CD calling `PATCH` on their own row (e.g., update name) succeeds.
- A CD calling `PATCH` on a sibling CD is rejected by RLS.

### AC-6 — PO walled off from institution data (D8)
- The PO (via middleware, with `app.is_platform_owner = true` but no `app.current_client_id`) querying `app_user` sees ZERO rows.
- The PO calling `GET /api/v1/users`, `GET /api/v1/institutions`, `GET /api/v1/homeworks`, `GET /api/v1/fees` returns ZERO rows.
- The PO calling `POST /api/v1/users` (write) is rejected by RLS on `app_user` — PO has no `current_client_id` match.
- The PO can CRUD `client_user` rows because the new table's RLS explicitly allows PO.

### AC-7 — Defense-in-depth preserved (D8)
- `require_permission` still bypasses for the PO on the existing `/api/v1/users`, `/api/v1/institutions` etc. — but the data is filtered to ZERO rows by RLS.
- Existing RLS policies on `app_user`, `institution`, `fees`, `homework` are NOT modified by this feature.

### AC-8 — Mirror lifecycle event table (D10)
- A NEW `client_user_lifecycle_event` table exists with actor, reason, timestamp columns.
- Every `client_user.lifecycle_status` transition (invited → active → suspended → archived) inserts a corresponding row in `client_user_lifecycle_event`.
- The CD does NOT drive their own lifecycle transitions (only the PO does), EXCEPT the `invited → active` transition which the CD triggers by completing the invite flow.

### AC-9 — Strict-fail login (D14)
- A Supabase Auth user with no `user_metadata.user_tier` flag is rejected at login with a clear error ("Account requires reconfiguration").
- After the go-live wipe, every Supabase Auth user (except PO `admin@school-erp.com`) is created through our backend which sets `user_tier` at creation.

### AC-10 — Migration rollout (D13)
- Migration 011 creates `client_user`, moves any existing `app_user` rows with `institution_id IS NULL` into `client_user`, backfills `user_metadata.user_tier` on those users.
- Migration 012 ALTERs `app_user.institution_id` to NOT NULL. The ALTER succeeds because no NULL rows remain.
- `UserCreateDTO.institution_id` is required at the API layer after migration 012.

---

## 6. Risks

| ID | Risk | Mitigation | Per |
|---|------|-----------|-----|
| R1 | **RLS misconfiguration on the new `client_user` table.** A wrong policy could expose one CD's row to another CD, or could accidentally grant the PO write access to institution tables (if the policy is broad). | Implement RLS policy tests early in the spec phase. Belt-and-braces: PO CRUD policy + CD own-row policy as separate policy stanzas. | D5, D8 |
| R2 | **`user_metadata.user_tier` drift between Supabase Auth and our tables.** If a row in `client_user` is deleted but the Auth user keeps `user_tier=client_leadership`, login will fail with "user not found" without a clear remediation. | The `DELETE` PO endpoint must mutate the Supabase Auth user too (delete or block) in a single transactional operation. The spec must define the auth-side cleanup step. | D2 |
| R3 | **JWT replay during suspend window.** A suspended CD's HS256 JWT keeps working until natural expiry (up to 3600s by default). A malicious CD could act in that window. | Rely on short HS256 JWT TTL (C-08 `auth.jwtExpirySeconds`). Revisit token revocation at production security review (D12). Document the window explicitly in the spec. | D12 |
| R4 | **Migration order risk.** Migration 012 ALTERs `app_user.institution_id` to NOT NULL. If migration 011 did NOT successfully move all NULL rows out, migration 012 fails mid-run leaving the DB in a half-applied state. | Migration 011 must be idempotent and assert "0 NULL rows remaining" before completing. Migration 012 must be a no-op if the assertion fails. | D13 |
| R5 | **Casbin dual-source policy loader.** The Casbin enforcer currently loads role-permission mappings from `role_assignment` only. Adding `client_user` as a second source increases loader complexity and the risk of stale role data. | The policy loader is extended (not replaced) to ALSO read `client_user.role_id` for client-leadership-role mappings. Load order is deterministic. Tests cover both sources. | D3 |
| R6 | **Casbin policy reload on CD role change.** If the PO changes a CD's role (e.g., from `client_director` to a future `client_admin` role), the Casbin enforcer's in-memory state may be stale. | Define a reload trigger; or rely on the policy-loader's existing startup-only loading and require an app restart for role changes (acceptable for low-volume CD operations). | D3 |
| R7 | **Greenfield wipe operational risk.** Deleting existing Supabase Auth users before go-live (per D14) means ALL existing test data tied to those users becomes orphaned (login_audit, role_assignment, app_user, etc.). | The wipe is a documented one-shot operation. Migrations handle orphaned rows (cascade delete or soft-archive). | D14 |
| R8 | **Invite URL leakage.** The PO sees the single-use invite URL (D7). A malicious PO could use it to set a CD's password. The pool of people with PO credentials is presumed small. | The invite URL is single-use and short-lived (existing C-03 invite JWT TTL). After the CD completes activation, the URL is dead. Note this in security review. | D7 |
| R9 | **`user_category_id` for CDs.** Today `user_category_id` on `app_user` was used for CDs as "Executive Leadership". Now that CDs live in `client_user`, the category semantics may need a separate `client_user_category` lookup OR reuse the existing `user_category` table. | Open question — see §8. The spec/design phase must answer it. | — |

---

## 7. Open Questions

Most decisions were locked in the grill-me session. Remaining open questions to resolve at spec or design stage:

1. **Token revocation mechanism — deferred.** Resurface at production security review (per D12).
2. **Exact transition arcs for `client_user_lifecycle_event`.** Confirmed states: `invited → active → suspended → archived`. Permitted arcs to be defined in spec (e.g., can `invited` go directly to `archived`? Can `suspended` go back to `active`? Can `active` go to `archived` directly?).
3. **`user_category_id` for `client_user` rows.** Should `client_user` reuse the existing `user_category` lookup table (with "Executive Leadership" applied today), OR introduce a separate `client_user_category` lookup OR drop the category concept entirely for client-leadership (since the role column already conveys client_director / client_admin)? — Open, see Risk R9.
4. **Does the Institution Admin gain any new capability now that CDs no longer compete for `app_user` rows?** Likely no behavior change, but spec must confirm IA's permission set is unchanged.
5. **Bootstrap endpoint request shape.** The grill-me session locked that the PO provides `{email, name, role}` for bootstrap. Should the endpoint also accept an optional `user_category_id`, or compute it from the role? — Open.
6. **CD-initiated `DELETE` of their own account.** Can a CD delete themselves (announcing departure)? Or only the PO can delete CDs? — D5 implies PO-only deletes; spec must confirm.

---

## 8. Companion Links

### 8.1 Source-of-truth docs
- `docs/specs/platform-owner-separation.md` — PO-as-Auth-only decision history (D28, D11 source)
- `docs/prd/c-01-tenant-institution.md` — tenant/institution background, current PO client-creation flow
- `openspec/specs/tenant-institution/spec.md` — live spec source of truth (DO NOT edit in this phase)

### 8.2 Code references (read for context, not modified in PRD phase)
- `backend/kernel/middleware.py` — current PO bypass (D8, D28 source)
- `backend/kernel/auth/services/service.py` — login flow extended (D2, D9)
- `backend/kernel/auth/services/invite_token.py` — invite machinery reused (D6)
- `backend/kernel/authz/services/policy_loader.py` — Casbin loader extended (D3)
- `backend/migrations/versions/002_c02_identity_user_management.py` — `app_user` RLS that stays (D8)
- `backend/migrations/versions/008_nullable_institution_id.py` — what D13 reverses
- `backend/migrations/versions/007_platform_owner_rls.py` — RLS pattern for PO bypass

### 8.3 Templates
- `docs/reference/document-template.md` — PRD template
- `docs/prd/c-08-configuration-framework.md` — format reference
- `docs/prd/c-01-tenant-institution.md` — example kernel PRD

---

> **End of PRD**
> **Version:** 1.0
> **Date:** 2026-08-01
> **Decisions:** 14 locked (D1–D14)
> **Status:** Ready for SDD flow (impact classification → proposal → spec → design → tasks → apply → verify → archive)