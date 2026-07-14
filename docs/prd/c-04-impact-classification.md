# Impact Classification — C-04 Authorization

> **Status:** Impact classification (input to prd-to-sdd phase)
> **Capability:** C-04 — Authorization
> **Decisional inputs:** `docs/prd/c-04-authorization.md` (PRD), grill-me session (33 locked decisions, 2026-07-13)
> **Verification:** `openspec/specs/tenant-institution/spec.md` exists (C-01 behavioral spec, archived). `openspec/specs/identity-user-management/spec.md` exists (C-02 behavioral spec, archived). No `authorization` spec exists yet. `openspec/specs/authentication/spec.md` exists (C-03 behavioral spec, archived).

---

## Classification
- Domain status: **NEW** (C-04 has no existing OpenSpec spec)
- Delta type: **ADDED** (new domain) + **MODIFIED** (C-01 + C-02 behavioral contract changes)
- Cross-cutting: **YES** — C-04 retrofits C-01 and C-02 endpoints with authorization; moves Casbin model from C-01; adds `platform_owner` row to C-02's `role` table
- Recommended OpenSpec domain name: `authorization`
- Recommended OpenSpec change name: `add-c04-authorization`

## Reasoning

### C-04 is a NEW domain (ADDED)

The `openspec/specs/` directory contains `tenant-institution/spec.md` (C-01), `identity-user-management/spec.md` (C-02), and `authentication/spec.md` (C-03). There is no `authorization` spec. This makes C-04's primary delta type ADDED — a brand-new domain introducing the `permission` catalog, `role_permission` mapping, Casbin enforcer singleton, `require_permission` FastAPI dependency, and ownership enforcement.

### C-04 MODIFIES C-01's behavioral contract

C-01's spec (archived in `2026-07-08-add-c01-tenant-institution`) currently defines C-01 endpoints as operating without authorization — they rely on RLS for data isolation and JWT validation for authentication. C-04 changes this: every C-01 endpoint (~15) now requires a specific permission via `Depends(require_permission(...))`. This is a behavioral change to C-01's domain — endpoints that previously allowed any authenticated user now gate on role+permission+scope.

Specifically, C-01's spec will need MODIFIED deltas for:
- **All C-01 route handlers** — each endpoint gains `require_permission(resource, action, client_id=..., institution_id=...)` dependency (D16)
- **Casbin model relocation** — `casbin_model.conf` moves from `business/tenant_institution/` to `kernel/authz/` (D14)
- **Casbin enforcer ownership** — `build_enforcer()` removed from C-01; C-01's `register_casbin_policies(enforcer)` hook receives the central enforcer from C-04 (D14)
- **C-01 test adaptations** — test fixtures must include `role` + `permission` + `role_permission` seed data or override the `get_enforcer()` dependency (D20)

### C-04 MODIFIES C-02's behavioral contract

C-02's spec (archived in `2026-07-11-add-c02-identity-user-management`) currently defines C-02 endpoints as operating without authorization. C-04 changes this: every C-02 endpoint (~12) now requires a specific permission. Additionally, C-02's `role` table gains a `platform_owner` row.

Specifically, C-02's spec will need MODIFIED deltas for:
- **All C-02 route handlers** — each endpoint gains `require_permission(resource, action, ...)` dependency (D16)
- **`platform_owner` role row** — C-02's `role` lookup table gains one new row via C-04's migration (D28)
- **C-02 test adaptations** — test fixtures must include permission seed data or override the dependency (D20)

### C-04 does NOT modify C-03's spec

C-03's authentication spec (archived in `2026-07-12-add-c03-authentication`) is unchanged. C-04 reads `TenantContext.roles` from the middleware (D13), which is populated by C-03's D7 middleware lookup. No C-03 endpoint is retrofitted — auth endpoints (login, activate, OTP, password reset) are unauthenticated by design and don't need authorization. C-04's Casbin policies don't cover C-03 endpoints.

### Why cross-cutting is YES

C-04 is the first capability to retroactively enforce authorization on two previously-completed capabilities:
- **C-04 depends on C-01** — C-04 reads C-01's D11 Casbin policies for platform-level roles. C-04's Casbin model originated in C-01. C-04 retrofits C-01 endpoints.
- **C-04 depends on C-02** — C-04's `role_permission` table has an FK to C-02's `role` table. C-04 adds a `platform_owner` row to C-02's `role` table. C-04 retrofits C-02 endpoints.
- **C-04 depends on C-03** — C-04 reads `TenantContext.roles` populated by C-03's middleware (D7). No C-03 modification.

This makes C-04 cross-cutting. The MODIFIED deltas to C-01 and C-02 are genuine behavioral changes (endpoints now enforce authorization), not mere boundary declarations. The `platform_owner` row addition to C-02's `role` table is a data-level change to an archived capability's table.

## ADDED requirements (high-level — C-04's new domain)

These are the requirement areas that will become requirements/scenarios in `specs/authorization/spec.md` during prd-to-sdd. Each maps to PRD §7 Acceptance Criteria and grill-me decisions.

- **Permission catalog** — `permission` table with 26 Phase 1 permissions (14 C-01 + 12 C-02) in `resource.action` format. Columns: `id` (UUID PK), `name` (unique), `description`, `resource`, `action`, `created_at`. No RLS (global data). Seeded in migration. (D8, D18, D30, AC-1, AC-3)
- **Role-permission mapping** — `role_permission` table mapping C-02's `role` rows to `permission` rows. FK to C-02's `role.id`. 7 C-02 roles mapped to their permitted resource.actions per §2.1.2 of the PRD. No RLS (global data). Seeded in migration. (D8, D15, D26, AC-2, AC-3)
- **`platform_owner` role row** — C-02's `role` table gains one new row: `platform_owner`. Added by C-04's migration (not by a C-02 migration). Assigned to the platform owner user via `role_assignment` (C-03 bootstrap). C-04's `role_permission` does NOT map `platform_owner` — it gets `*.*` from C-01's D11 Casbin policies. (D27, D28, AC-18, AC-19)
- **Casbin model relocation** — `casbin_model.conf` moves from `business/tenant_institution/` to `kernel/authz/`. No content changes to the model (it already supports RBAC role hierarchy + ABAC scope checks). C-01's `register_casbin_policies(enforcer)` hook receives the central enforcer and continues to add D11 policies using the relocated model path. (D4, D14, D25, AC-17)
- **Casbin enforcer singleton** — App factory creates exactly one Casbin enforcer from the model at `kernel/authz/casbin_model.conf`. Calls `register_casbin_policies(enforcer)` on each module manifest in dependency order (C-01 → C-02 → C-03 → C-04). Enforcer available via `get_enforcer()` dependency. (D10, D29, AC-11)
- **`require_permission` FastAPI dependency** — Dependency signature: `require_permission(resource: str, action: str, client_id: UUID | None = None, institution_id: UUID | None = None, owner_id: UUID | None = None)`. Reads `TenantContext.roles` from contextvar (D13). Builds Casbin subject (`{role, client_id, institution_id}`) and object (`{name: resource, client_id, institution_id}`). Calls `enforcer.enforce(sub, obj, action)`. Two-step enforcement: (1) Casbin for role+scope, (2) app-level ownership check if `owner_id` provided. Returns silently on pass; raises 403 `HTTPException` on deny. (D5, D7, D12, D19, D22, D31, AC-4 through AC-10)
- **C-04's `register_casbin_policies(enforcer)` hook** — `on_startup` hook reads `role_permission` from DB into an in-memory dict. `register_casbin_policies` iterates the dict: `enforcer.add_policy(role_name, resource, action, scope)` + `enforcer.add_grouping_policy(user_role_name, casbin_role_label)`. Policies are in-memory after startup (D11). (D24, D29, AC-12, AC-13)
- **C-01 endpoint retrofit** — Every endpoint in `backend/business/tenant_institution/routes/` (~15) gains `Depends(require_permission(resource, action, client_id=..., institution_id=...))`. C-01's `build_enforcer()` is removed. (D14, D16, D20, AC-14, AC-16)
- **C-02 endpoint retrofit** — Every endpoint in `backend/kernel/user/routes/` (~12) gains `Depends(require_permission(resource, action, ...))`. Read endpoints for own profile use `owner_id` parameter for ownership check (D22). (D16, D20, AC-15)
- **Module manifest + dependency integrity** — C-04's `AuthenticationManifest` registers routes, Casbin policies, CLI commands, and startup hooks via the ModuleManifest Protocol (A5). `kernel/authz/` respects A3 (kernel → ∅): imports only from `kernel/` packages and third-party. A4 (acyclic): C-04 (Level 3) → C-02 (Level 2) is allowed; reverse is blocked. (D9, D32, AC-20, AC-21)
- **Testing with real Casbin enforcer** — C-04 tests build a Casbin enforcer with the real model and seed policies, then assert `enforcer.enforce(subject, object, action)` returns expected results for each role-permission-scope combination. C-04 tests also test the `require_permission` dependency in isolation. C-01/C-02 retrofit tests continue to pass via seed data or dependency override. (D17, D20, AC-22 through AC-24)

## MODIFIED requirements (C-01 behavioral contract changes)

C-01's spec must be updated with MODIFIED deltas reflecting that all C-01 endpoints now enforce authorization via `require_permission`. These are genuine behavioral changes to C-01's domain.

- **C-01 route handlers gain authorization** — Every C-01 endpoint (client, institution, org_unit, institution_type) must include `Depends(require_permission(resource, action, client_id=..., institution_id=...))`. The endpoint now returns 403 if the calling user's role lacks the required permission or if scope checks fail (cross-institution, cross-tenant). (D16, AC-14)
- **C-01 Casbin model is relocated** — The file `business/tenant_institution/casbin_model.conf` is moved to `kernel/authz/casbin_model.conf`. All references in C-01's `policies.py` and tests must be updated. (D14, AC-17)
- **C-01 `build_enforcer()` is removed** — C-01 no longer creates its own Casbin enforcer. Its `register_casbin_policies(enforcer)` hook receives the central enforcer from the app factory. Any test code that called `build_enforcer()` must use the centrally-provided enforcer instead. (D14, AC-16)
- **C-01 tests adapted for authorization** — Existing C-01 tests must include `role` + `permission` + `role_permission` seed data or use `app.dependency_overrides[get_enforcer]` to bypass authorization. Tests must not fail due to missing permissions. (D20, AC-24)

## MODIFIED requirements (C-02 behavioral contract changes)

C-02's spec must be updated with MODIFIED deltas reflecting that all C-02 endpoints now enforce authorization and the `role` table gains a `platform_owner` row.

- **C-02 route handlers gain authorization** — Every C-02 endpoint (user, user_profile, role_assignment, user_identifier, user_category, role) must include `Depends(require_permission(resource, action, ...))`. Profile read/update endpoints use `owner_id` for ownership checks (D22). (D16, AC-15)
- **`platform_owner` row in C-02's `role` table** — C-04's migration 004 inserts a `platform_owner` row into the `role` lookup table. This row is assigned to the platform owner user via `role_assignment` by the C-03 bootstrap CLI. C-04's `role_permission` does NOT map this role — it receives `*.*` from C-01's D11 Casbin policies. (D28, AC-18, AC-19)
- **C-02 tests adapted for authorization** — Existing C-02 tests must include permission seed data or use `app.dependency_overrides` to bypass `require_permission`. Tests must not fail due to missing permissions. (D20, AC-24)

## REMOVED requirements

None. No existing requirements are removed from any domain. C-01's `build_enforcer()` function is removed as a code artifact but its behavioral effect (enforcer creation) is replaced by C-04's app-factory-created singleton — the behavior is consolidated, not removed.

## Cross-cutting concerns

### Test infrastructure impact
C-01 and C-02 have 165 + 12 = 177 existing tests. After retrofitting with `require_permission`, these tests need:
1. Seed data: `role`, `permission`, and `role_permission` rows in test fixtures, OR
2. Dependency override: `app.dependency_overrides[get_enforcer]` to return a permissive enforcer

Option 1 is preferred because it validates that the real authorization policies work end-to-end. Option 2 may be used for tests that don't exercise C-04 directly.

### Import-linter contracts
No new contracts needed (D32). Existing A3 (`kernel → ∅`) covers `kernel/authz/`. A4 (acyclic) is maintained by tier ordering (C-04 Level 3 → C-02 Level 2 → C-01a Level 1). C-01 (business) imports from C-04 (kernel) via `Depends(require_permission(...))` — business → kernel is allowed by A3.

### Migration strategy
C-04 introduces one migration `004_c04_authorization.py` that:
1. Creates `permission` table + seeds 26 rows
2. Creates `role_permission` table + seeds ~40 rows
3. Inserts `platform_owner` row into C-02's `role` table
4. Does NOT modify C-02's `role` table schema — only adds one row

### Startup sequence impact
The app factory (`kernel/app_factory.py`) gains one new responsibility: creating the Casbin enforcer and calling `register_casbin_policies(enforcer)` on each manifest. This is a code change to kernel infrastructure, not a behavioral spec change to any existing domain.

### Platform owner role assignment
The `platform_owner` row is added to the `role` table by C-04's migration, but it must be assigned to the platform owner user via `role_assignment`. The C-03 bootstrap CLI (`kernel/auth/bootstrap.py`) is responsible for creating the `role_assignment` row during the first-run bootstrap.

## Dependency impact summary

| Domain | Status | Spec changes | Code changes | Test changes |
|---|---|---|---|---|
| `authorization` (C-04) | **NEW** | ADDED spec | Full module | New test file |
| `tenant-institution` (C-01) | **MODIFIED** | MODIFIED spec | ~15 endpoints + `build_enforcer()` removal | Seed data or override |
| `identity-user-management` (C-02) | **MODIFIED** | MODIFIED spec | ~12 endpoints + `platform_owner` role row | Seed data or override |
| `authentication` (C-03) | **UNCHANGED** | None | None | None |
| `kernel` (infrastructure) | **MODIFIED** | None | `app_factory.py` — enforcer creation | None |

## Appendix: Change name and domain structure

- **Recommended change name:** `add-c04-authorization`
- **Delta spec domains:**
  - `specs/authorization/spec.md` — ADDED (18 requirement areas)
  - `specs/tenant-institution/spec.md` — MODIFIED (4 requirement areas)
  - `specs/identity-user-management/spec.md` — MODIFIED (3 requirement areas)
