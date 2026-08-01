## Context

The platform today models all users in one table — `app_user` of the C-02 Identity & User Management capability. Migration 008 (`008_nullable_institution_id.py`) made `app_user.institution_id` nullable to support one special population: the **Client Director** (CD), who manages an entire client (school chain) and has no institution.

This single-table model has three concrete problems surfaced during C-08 journey-flow testing:

1. **Bootstrap problem.** When a Platform Owner (PO) creates a new client and tries to bootstrap its first Client Director, they cannot call `POST /api/v1/users` (the standard create-user endpoint) because the PO has no `client_id` in their JWT — the endpoint requires tenant context. The documented Flow 1 in `01_platform_owner.html` works around this by calling the Supabase REST API directly with `service_role` to insert `app_user` and `role_assignment`. That workaround bypasses our backend: no audit logging, no service-layer validation, exposed admin key in the browser.
2. **RLS bypass failure.** Even that Supabase-direct workaround fails on the cloud DB. The `app_user` INSERT RLS policy requires `is_platform_owner() OR client_id = current_client_id()` — both functions read PostgreSQL session variables (`app.is_platform_owner`, `app.current_client_id`) ONLY our middleware sets. PostgREST never sets those variables, so the insert fails with `42501 permission denied for table app_user`.
3. **Visibility tension.** the PO must "create a client user" (provision a tenant) without "gaining access to client data" (students, teachers, grades, fees). On one table these two acts are hard to separate: any PO CRUD-access to `app_user` is also a PO read opportunity across ALL institution rows.

This change resolves all three by introducing a **two-tier user model**: the `client_user` table holds all client-leadership-scope users, the `app_user` table becomes institution-only (with `institution_id` NOT NULL), and RLS on institution tables remains the hard wall keeping the PO from tenant data.

Stakeholders: PO (creates/operates clients), CD (manages one client across all its institutions), existing Institution Admin / Teacher / Student / Parent tiers (in `app_user`, unchanged in behavior).

## Goals / Non-Goals

**Goals:**
- PO can create, list, suspend, and revoke Client Directors via audit-logged backend endpoints under `/api/v1/platform/clients/$ID/users/*`.
- PO gains ZERO row visibility on `app_user`, `institution`, `homework`, `fees` (RLS stays the wall).
- CDs log in via a custom HS256 JWT, manage own profile (own row only), manage all institutions under their client through the existing `POST /api/v1/users`.
- The hard data-model invariant "every `app_user` row belongs to exactly one institution" is enforced at the DB level, not just by convention.
- Bootstrap email-free (Phase 1): the PO forwards the invite URL out-of-band.

**Non-Goals:**
- PO does NOT move into a tier-table (PO stays Supabase Auth only per D11).
- NO token revocation list (per D12 — short HS256 JWT TTL is the natural-expiry safety net; revisit at production security review).
- NO SMTP-based email delivery of invites (Phase 1 returns the URL in the API response; future email can displace this).
- NO self-heal fallback for legacy Supabase Auth users (per D14 — strict-fail with greenfield wipe instead).
- NO new permissions retrofit in `require_permission` — the platform endpoints use `require_platform_owner`.
- NO migration of the throwaway test frontend's `01_platform_owner.html` flow to the new bootstrap endpoint in this change. That's a UI follow-up tracked separately.

## Decisions

### D1 — Two physical tables vs single table with a tier column

**Choice:** Two physical tables — new `client_user` + existing `app_user`, with `app_user.institution_id` NOT NULL.

**Rationale:** The two populations have structurally different shapes (CD has a `client_id` but no `institution_id`; institution users have both; CD's role sits on the row directly, institution users' role sits in `role_assignment`). They have structurally different access policies (PO CRUDs CDs; CD-reads-own-row; institution users are scoped by `client_id` AND `institution_id`). A single-table-with-`tier`-column would force nullable `institution_id`, a wider RLS policy, and a more complex loader — bringing back the exact friction this change is meant to remove. Two tables keeps each tier's schema and RLS minimal and self-documenting.

### D2 — Login table lookup via Supabase `user_metadata.user_tier`

**Choice:** Read `user_metadata.user_tier` from the Supabase Auth response and branch.

**Rationale:** Stamping `user_tier` at Auth user creation time (set by the backend whenever a user is created) makes login one Supabase call + one targeted table query. The alternative — querying both tables by auth `user_id` and OR-ing — would be one extra DB round-trip on every login. The cost of an explicit Supabase Auth coupling is reasonable: the platform already depends on Supabase Auth for credentials.

### D3 — Role as a column on `client_user` (no separate role_assignment)

**Choice:** `client_user.role_id` FK to `role`, no `client_role_assignment` table.

**Rationale:** Client-leadership has very few roles — `client_director` today, plus future `client_admin`, `billing_contact`. A CD has exactly ONE client-leadership role at a time. A separate role-assignment table would replicate machinery that buys us nothing for such a tiny role set. The Casbin policy loader reads `client_user.role_id` as a SECOND source alongside the existing `role_assignment` source for institution users.

### D6 — Reuse C-03 invite infrastructure

**Choice:** Reuse `kernel/auth/services/invite_token.py` — the C-03 invite JWT machinery — to mint CD bootstrap invites.

**Rationale:** The platform already has an invite flow (C-03) used to transition `app_user` rows from `invited` to `active`. Reusing it means zero new JWT-secret machinery, a tested token verification path, and consistent lifecycle states (`invited`/`active`) for both tiers. The only NEW surface is the `/api/v1/platform/clients/$ID/users` bootstrap endpoint that DRIVES the existing invite machinery.

### D9 — Custom HS256 JWT for CDs (extends the PO JWT pattern)

**Choice:** CD login mints a custom HS256 JWT carrying `{sub, user_tier, client_id, role_id, exp}`.

**Rationale:** The PO already uses a custom HS256 JWT (not the Supabase JWT) because the platform needs to encode platform-specific claims. The same pattern extends to CDs: mint our own HS256 token, encode `user_tier` and the relevant scope (`client_id`, `role_id`). This avoids middleware's per-request DB lookup — claims are read directly off the JWT. The TTL reuses C-08's `auth.jwtExpirySeconds` (per D12) so this change introduces no new configuration surface.

### D12 — Token revocation deferred

**Choice:** No revocation list in Phase 1.

**Rationale:** A revocation list (denylist of HS256 JWTs by `jti` or revocation-by-user-id) is a real production security feature. Phase 1 of the platform is pre-launch; the small number of POs and the short JWT TTL (C-08 `auth.jwtExpirySeconds` default 3600s) bounds the persisted-token replay window after a suspend. Documented as `R3` in the PRD; revisit at production security review.

### D13 — Two-migration rollout (011 + 012)

**Choice:** Migration 011 creates `client_user`, moves any `app_user` rows with `institution_id IS NULL` into `client_user`, and backfills `user_metadata.user_tier`. Migration 012 ALTERs `app_user.institution_id` to NOT NULL.

**Rationale:** Splitting the migration into two steps means migration 012 can be safely applied on a 011-cleaned database (assertion: zero NULL `institution_id` rows remaining). Out-of-order application of 012 fails loudly on the assertion rather than silently leaving broken rows.

### D14 — Strict-fail login + greenfield wipe (no self-heal)

**Choice:** A Supabase Auth user without `user_metadata.user_tier` is rejected at login. The operator wipes legacy users before go-live (except the PO `admin@school-erp.com`).

**Rationale:** A self-heal fallback in login code ("try `client_user` first, then `app_user`") restores complexity the tier model was meant to remove and has a small but real risk of wrong-tier attribution. Strict-fail forces explicit cleanup. Kicking the small operational cost of wiping a few test users before launch avoids a long-term liability in the login critical path.

## Risks / Trade-offs

| ID | Risk / Trade-off | Mitigation |
|---|---|---|
| R1 | RLS misconfiguration on `client_user` exposes one CD's row to another CD. | Implement RLS tests early in the apply phase as belt-and-braces: PO CRUD policy + CD own-row policy as SEPARATE policy stanzas (AddPolicy for `client_user` not shared with any other table). |
| R2 | `user_metadata.user_tier` drift — `client_user` deleted but Auth user keeps `user_tier = "client_leadership"` — causes login to return "user not found" unclearly. | The PO `DELETE` endpoint MUST mutate the Supabase Auth user too (block or delete) in one transactional operation. Spec mandates this; design tracking task enforces it. |
| R3 | Suspended-CD JWT replay window (per D12). | Bounded by `auth.jwtExpirySeconds` (default 3600s). Revisit at production security review. Documented in the spec scenario "Suspended CD replay window". |
| R4 | Migration 012 fails mid-ALTER if 011 did not clean NULL rows. | Migration 011 asserts "0 NULL rows remaining" before completing. Migration 012 wraps the ALTER in a check that the post-011 assertion holds; if not, it no-ops and reports. |
| R5 | Casbin dual-source policy loader is more complex; risk of stale role data. | Loader's load order is deterministic; tests cover both sources. The role on the CD JWT itself is the AUTHORITATIVE source per request (the enforcer only sees roles at startup), avoiding per-request stale reads. |
| R6 | PO sees the invite URL (D7) — can PO use it to set a CD's password? | Invite URL is single-use + short-lived; using it only lets PO set the CD's password, not impersonate later. Acceptable for the small PO credential pool; revisit at security review. |
| R7 | Greenfield wipe orphans existing test data tied to legacy Auth users. | Wipe is documented one-shot; migrations cascade-delete or soft-archive orphans. |
| R8 | Two physical tables = two paths for any "all-users" reporting feature. | No such feature exists in Phase 1. If added later, it queries both tables (UNION view) and is owned by a future capability, not this one. |
| R9 | `user_category_id` semantics for `client_user` rows are ambiguous: reuse existing `user_category` lookup, introduce `client_user_category`, or drop the concept? | This is an open question carried from the PRD; the apply phase resolves it. The trade-off: reuse (less code, slight semantic overload) vs new lookup (clean semantics, more code) vs drop (relies on `role_id` to convey category). Provisional recommendation: reuse the existing `user_category` lookup with "Executive Leadership" for CDs, mirroring current convention; final call at apply. |
| R10 | Migration 011's backfill of `user_metadata.user_tier` on Supabase Auth is a network call INSIDE a DB migration — failure could leave a half-applied migration. | Migration 011 implements the Supabase backfill step with retry + idempotency check; a backfill failure marks the migration as not-yet-applied and rolls back the DB-side changes. Migration is RE-runnable. |

## Open Questions (carried to the apply phase from PRD §7)

1. Exact transition arcs for `client_user_lifecycle_event` (`invited → active → suspended → archived`) — which arcs are permitted (e.g., can `invited` go directly to `archived`? Can `suspended` go back to `active`?).
2. `user_category_id` for `client_user` rows (see risk R9).
3. Whether the bootstrap endpoint also accepts an optional `user_category_id`, or computes it from `role`.
4. Whether a CD can DELETE their own account (provisional: PO-only).
5. Token revocation mechanism — deferred to production security review.

These questions do NOT block the spec/design contract — the apply phase resolves them in code and tests.