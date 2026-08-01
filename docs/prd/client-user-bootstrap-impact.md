# Impact Classification — Client User Bootstrap & Tier Separation

> **Status:** Impact classification (input to prd-to-sdd phase)
> **Feature:** Client User Bootstrap & Tier Separation
> **Decisional inputs:** `docs/prd/client-user-bootstrap.md` (PRD), grill-me session (14 locked decisions, D1–D14, 2026-08-01)
> **Verification:** `openspec/specs/tenant-institution/spec.md` exists (C-01). `openspec/specs/platform-owner-separation/spec.md` exists. `openspec/specs/platform-owner-followups/spec.md` exists. `openspec/specs/configuration/spec.md` exists (C-08). No active changes in `openspec/changes/` (all 11 prior changes archived).
> **Capability layer:** **Kernel** (lives in `backend/kernel/user/`, `backend/kernel/auth/`, `backend/kernel/authz/`, NOT `backend/business/`)

---

## Classification

- Domain status: **NEW** (the `client_user` entity has no existing OpenSpec spec)
- Delta type: **ADDED** (new domain — `client_user` + `client_user_lifecycle_event`) + **MODIFIED** (multiple existing domains' behavioral contracts change) + **REMOVED** (one specific behavior — `app_user.institution_id` nullable — is reversed)
- Cross-cutting: **FULL** — this feature touches 4 existing live specs (`tenant-institution`, `platform-owner-separation`, `platform-owner-followups`, `configuration`) plus introduces a 5th new spec. The change is fundamentally cross-cutting because it restructures the user identity model that every other capability consumes.
- Recommended OpenSpec domain name: `client-user-bootstrap` (new) — separate from `tenant-institution` because the entity (`client_user`) is distinct from any C-01 entity and the actor relationship (PO provisions CD) is platform-tier.
- Recommended OpenSpec change name: `add-client-user-bootstrap`

---

## Reasoning

### This feature introduces a NEW domain (`client_user`)

The `openspec/specs/` directory contains `tenant-institution/`, `platform-owner-separation/`, `platform-owner-followups/`, `configuration/`. There is NO spec covering a `client_user` entity or the PO's responsibility to provision Client Directors. The primary delta type is **ADDED** — a brand-new kernel domain introducing:

- `client_user` entity (client-leadership-scope users, role-as-column, lifecycle)
- `client_user_lifecycle_event` entity (forensic history, mirrors `app_user`'s event table per D10)
- The `/api/v1/platform/clients/$ID/users/*` endpoint surface (D4)
- The bootstrap invite flow (D6, D7)
- The CD custom HS256 JWT (D9)

### This feature MODIFIES `tenant-institution` (C-01)

C-01's spec defines the PO's client-creation flow. Today, the PO creates a client via `POST /api/v1/platform/clients` and then bootstraps the first CD via **direct Supabase REST API calls** (the C-01 PRD noted this as a known workaround). This feature:

- **REMOVES the workaround** — the direct Supabase REST API path for `app_user` / `role_assignment` inserts is no longer the documented bootstrap path. It is replaced by `POST /api/v1/platform/clients/$ID/users`.
- **MODIFIES the client-creation journey** — after creating + activating a client, the PO has an explicit step to bootstrap the CD through our backend (audit-logged, transactional, RLS-safe).

The MODIFIED delta to `tenant-institution` describes "the PO's bootstrap journey now uses `/api/v1/platform/clients/$ID/users` instead of direct Supabase calls." The C-01 client entity itself is unchanged.

### This feature MODIFIES `platform-owner-separation`

The Platform-Owner-Separation spec locked **D28 (PO bypasses Casbin `require_permission`) and D5 (PO blocked from endpoints requiring `client_id`)** as defense-in-depth. This feature DOES NOT touch those decisions (per our D8 — defense-in-depth is kept). However:

- **MODIFIES** the existing `is_platform_owner() OR client_id = current_client_id()` RLS policy pattern, specifically on the NEW `client_user` table — the PO can write to `client_user` because a NEW policy explicitly allows PO CRUD. This is a behavioral extension to the PO's reach, not a contraction. Documented in the `platform-owner-separation` spec as "PO can now CRUD a NEW table (`client_user`), still cannot read institution tables."
- **MODIFIES** the existing `require_platform_owner` dependency (currently used for `/api/v1/platform/clients` CRUD) to ALSO protect `/api/v1/platform/clients/$ID/users/*`. No new dependency; the same one is extended to a new endpoint surface.

### This feature MODIFIES `platform-owner-followups`

The platform-owner-followups spec defines the PO's behavioral contract after the PO-Auth-only migration. This feature adds a NEW responsibility — "the PO provisions Client Directors" — to the PO's behavioral contract. This is a MODIFIED delta:

- ADDED requirement: "PO can list / suspend / revoke Client Directors in any client via `/api/v1/platform/clients/$ID/users/*`."
- ADDED requirement: "PO bootstrap of a Client Director returns an invite URL; PO forwards it out-of-band."

### This feature MODIFIES `configuration` (C-08, lightly)

C-08's spec defines `auth.jwtExpirySeconds` as a platform-level config key governing JWT TTL. This feature depends on that key as the natural-expiry safety net for the suspended-CD JWT-replay window (per D12, Risk R3). C-08's behavior is unchanged; this feature only DOCUMENTS the dependency. A MODIFIED delta to `configuration` adds a requirement: "CD HS256 JWT TTL is governed by the existing `auth.jwtExpirySeconds` config key; this key serves double-duty as the natural revocation safety net for suspended CDs."

### This feature REMOVES a behavior in `tenant-institution` (D13 reversal)

Migration `008_nullable_institution_id.py` made `app_user.institution_id` nullable to support CDs living in `app_user`. With the CD moving to `client_user`, that rationale disappears. Migration 012 ALTERs `app_user.institution_id` to NOT NULL. This is a **REMOVED** requirement in `tenant-institution`:

- REMOVED: "`app_user.institution_id` is nullable to support client-leadership users without an institution." (Migration 008 behavior — reversed.)
- ADDED: "`app_user.institution_id` is NOT NULL; every `app_user` row belongs to exactly one institution. Client-leadership users live in `client_user`, not `app_user`."

### Why cross-cutting is FULL (not partial)

Unlike C-08 (which was partial cross-cutting — added rows to C-04 tables but no endpoint retrofits), this feature:

- Introduces a NEW spec domain (`client-user-bootstrap`)
- MODIFIES the PO's behavioral contract (`platform-owner-separation`, `platform-owner-followups`)
- MODIFIES the C-01 bootstrap journey (`tenant-institution`)
- MODIFIES the C-08 JWT TTL contract (`configuration`) — light touch but real
- Affects the login flow that EVERY actor uses (`/api/auth/login` — added `user_tier`-based table lookup per D2)
- Affects the middleware that EVERY request flows through (added `user_tier` claim handling per D9)

Every authenticated user of the platform will be touched by the login flow change. This is full cross-cutting.

---

## ADDED Requirements (high-level — the NEW `client-user-bootstrap` domain)

These are the requirement areas that will become requirements/scenarios in `specs/client-user-bootstrap/spec.md` during prd-to-sdd. Each maps to PRD AC-1 through AC-10 and grill-me decisions D1–D14.

### Two-tier user model

- **`client_user` table** — holds client-leadership-scope users (Client Director + future Client Admins + Billing Contacts). Columns mirror `app_user` (email, name, user_category_id, lifecycle_status, created_at, updated_at) PLUS `role_id` (UUID FK → `role` — D3) PLUS `client_id` (UUID FK → `client`). NO `institution_id` column — a CD manages all institutions under their client. RLS allows PO CRUD + CD own-row SELECT/UPDATE. (AC-1, D1, D3, D5)
- **`client_user_lifecycle_event` table** — parallel event table mirroring `user_lifecycle_event`. Records every lifecycle transition (invited → active → suspended → archived) with actor, reason, timestamp. (AC-8, D10)
- **Login lookup by `user_metadata.user_tier`** — the `/api/auth/login` flow reads `user_metadata.user_tier` from the Supabase Auth response and queries `client_user` (for "client_leadership") or `app_user` (for "institution"). Strict-fail for users without the flag (per D14). (AC-2, AC-9, D2, D14)
- **CD custom HS256 JWT** — CD login mints a custom HS256 JWT carrying `{sub, user_tier, client_id, role_id, exp}`. No `institution_id`. Middleware reads claims directly; `app.current_client_id` is set from the JWT's `client_id`. (AC-2, D9)

### PO endpoint surface

- **`POST /api/v1/platform/clients/$ID/users`** (bootstrap) — body `{email, name, role}`. Creates Supabase Auth user in `invited` state, inserts `client_user` row with `lifecycle_status='invited'`, stamps `user_metadata.user_tier='client_leadership'`, mints invite JWT, returns invite URL. Requires `require_platform_owner`. (AC-3, D4, D6, D7)
- **`GET /api/v1/platform/clients/$ID/users`** (list CDs in client) — returns all CDs in client `$ID`. PO-only. (AC-4, D4)
- **`PATCH /api/v1/platform/clients/$ID/users/$UID`** (transition) — body `{new_state, reason}`. Transitions CD lifecycle; records `client_user_lifecycle_event`. PO-only. (AC-4, D4, D10)
- **`DELETE /api/v1/platform/clients/$ID/users/$UID`** (revoke) — archives CD. PO-only. (AC-4, D4)

### CD own-row management

- **CD SELECT own row** — `GET /api/v1/platform/clients/$ID/users/$SELF_ID` succeeds; RLS `WHERE id = current_user_id()`. (AC-5, D5)
- **CD UPDATE own row** — `PATCH /api/v1/platform/clients/$ID/users/$SELF_ID` (e.g., update display name). RLS `WHERE id = current_user_id()`. CD cannot PATCH siblings. (AC-5, D5)
- **CD denied list / insert / delete** — RLS blocks all rows but the CD's own. (AC-5, D5)

### Bootstrap invite flow

- **Mint invite JWT** — reuses existing `kernel/auth/services/invite_token.py`. The invite URL is returned in the API response (D7); PO forwards out-of-band. (AC-3, D6, D7)
- **CD accepts invite** — CD clicks the link, sets their own password, lifecycle transitions `invited → active`. (AC-3, D6)

### Defense-in-depth

- **PO cannot read institution rows** — even with `app.is_platform_owner = true` set by middleware, the PO lacks `app.current_client_id`, so RLS on `app_user`, `institution`, `fees`, `homework` returns ZERO rows. (AC-6, AC-7, D8)
- **Existing RLS policies unchanged** — `app_user`, `institution`, `fees`, `homework` RLS stay as-is. (AC-7, D8)
- **New `client_user` RLS allows PO** — the new table's RLS explicitly allows PO CRUD + CD own-row management. (D5, D8)

---

## MODIFIED Requirements (across existing domains)

### MODIFIED in `tenant-institution`

- **Bootstrap journey revision** — the PO's documented bootstrap journey switches from `/rest/v1/app_user` + `/rest/v1/role_assignment` direct Supabase calls to `POST /api/v1/platform/clients/$ID/users` through our backend. The C-01 PRD's described workaround becomes deprecated. (AC-3, D4, D6)
- **Client entity relationship** — the `client` entity now has a one-to-many relationship with `client_user` (a client has zero or more client-leadership users). This is a new relationship not previously in C-01.

### MODIFIED in `platform-owner-separation`

- **PO CRUD on `client_user`** — the PO's behavioral reach now includes a NEW table (`client_user`). The PO's bypass of `require_permission` (D28) stays; the RLS on `client_user` explicitly allows PO. Existing decisions D2, D3, D5 of the PO-separation spec are unchanged.
- **`require_platform_owner` extended** — the dependency used on `/api/v1/platform/clients` is now also used on `/api/v1/platform/clients/$ID/users/*`.

### MODIFIED in `platform-owner-followups`

- **PO responsibility additions** — the PO's behavioral contract now includes: bootstrap CDs (via invite), list CDs in any client, suspend CDs, revoke CDs. These are new responsibilities added to the PO's contract.

### MODIFIED in `configuration` (C-08, light touch)

- **`auth.jwtExpirySeconds` double-duty** — the existing platform-level config key now ALSO serves as the natural-expiry safety net for suspended-CD JWTs (per D12). The key itself and its semantics are unchanged; the spec documents the new downstream dependency.

---

## REMOVED Requirements (across existing domains)

### REMOVED in `tenant-institution`

- **`app_user.institution_id` nullable** — the behavior introduced by migration 008 (`008_nullable_institution_id.py`) is REMOVED. Migration 012 ALTERs `app_user.institution_id` to NOT NULL. Rationale: the CD no longer lives in `app_user`. (AC-1, AC-10, D13)
- **Direct Supabase REST API bootstrap workaround** — the documented path of inserting `app_user` + `role_assignment` via `$SUPABASE_URL/rest/v1/app_user` and `$SUPABASE_URL/rest/v1/role_assignment` is REMOVED from the documented journey. (The endpoints underlying it are not removed from Supabase; the *documented bootstrap flow* is removed.)

---

## Migration Order (critical — feeds into the spec/tasks phase)

The D13 two-migration rollout MUST be implemented in this order; out-of-order execution fails:

1. **Migration 011** — Create `client_user` + `client_user_lifecycle_event` tables. Move any existing `app_user` rows with `institution_id IS NULL` into `client_user`. Backfill `user_metadata.user_tier` on those users via Supabase Admin API.
2. **Migration 012** — `ALTER TABLE app_user ALTER COLUMN institution_id SET NOT NULL`. Safe because 011 cleared NULL rows. Also tighten `UserCreateDTO.institution_id` to required at the API layer.
3. **Greenfield wipe** (D14) — delete existing Supabase Auth users except `admin@school-erp.com` (the PO). This is an operational step documented in the tasks, not a migration.

---

## Open Questions Carried Forward

These are carried into the spec/design phase from the PRD:

1. Exact transition arcs for `client_user_lifecycle_event` (PRD §7.2).
2. `user_category_id` for `client_user` rows — reuse `user_category` lookup OR introduce `client_user_category` OR drop the concept (PRD §7.3, Risk R9).
3. Can Institution Admin gain any new capability now that CDs no longer compete for `app_user` rows? (PRD §7.4.)
4. Bootstrap endpoint request shape — should it also accept an optional `user_category_id`, or compute it from the role? (PRD §7.5.)
5. CD-initiated DELETE of their own account — allowed or PO-only? (PRD §7.6.)
6. Token revocation mechanism — deferred to production security review (PRD §7.1, D12).

---

## Companion Links

### Source-of-truth docs
- `docs/prd/client-user-bootstrap.md` — PRD (decisional source of truth, 14 locked decisions)
- `openspec/specs/tenant-institution/spec.md` — C-01 live spec (will receive MODIFIED + REMOVED deltas)
- `openspec/specs/platform-owner-separation/spec.md` — PO-separation live spec (will receive MODIFIED delta)
- `openspec/specs/platform-owner-followups/spec.md` — PO-followups live spec (will receive MODIFIED delta)
- `openspec/specs/configuration/spec.md` — C-08 live spec (will receive a light MODIFIED delta)

### Code references (read for spec/design phase, not modified in this classification)
- `backend/kernel/middleware.py` — login claim handling, RLS session vars
- `backend/kernel/auth/services/service.py` — login flow to extend
- `backend/kernel/auth/services/invite_token.py` — invite machinery to reuse
- `backend/kernel/authz/services/policy_loader.py` — Casbin loader to extend with `client_user` source (D3)
- `backend/kernel/user/services/service.py` — user creation service (will branch for `client_user` vs `app_user`)
- `backend/migrations/versions/002_c02_identity_user_management.py` — `app_user` RLS that stays (D8)
- `backend/migrations/versions/008_nullable_institution_id.py` — what D13 reverses
- `backend/migrations/versions/007_platform_owner_rls.py` — RLS pattern reference

---

> **End of Impact Classification**
> **Version:** 1.0
> **Date:** 2026-08-01
> **Domains touched:** 1 NEW (`client-user-bootstrap`) + 4 MODIFIED (`tenant-institution`, `platform-owner-separation`, `platform-owner-followups`, `configuration`) + 1 REMOVED behavior (in `tenant-institution`)
> **Status:** Ready for prd-to-sdd (proposal → spec → design → tasks → apply → verify → archive)