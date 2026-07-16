# Proposal — C-04 Authorization

## Why

Every business module in the School ERP — Attendance, Fees, Homework, Exams, Timetable — needs to know **what a user can do**. A Teacher should mark attendance but not create institutions. A Student should submit homework but not suspend other users. A Parent should view their child's grades but not change them. Without a centralized authorization capability, each module would implement its own permission checks — leading to fragmented access control, inconsistent enforcement, and security gaps.

C-04 provides the **single authorization gateway** for the entire platform. It answers: given an authenticated user (C-03), what operations are they allowed to perform on what resources, within what organizational scope? C-04 sits between C-03 (which knows who the user is) and every business module endpoint that needs to gate access.

Key architectural decisions: **Casbin owns the enforcement engine; C-04 owns the permission catalog and the role-to-permission mapping.** C-02's `Role` table (Teacher, HOD, Principal, Student, Parent, Staff, Admin) defines what a user IS — identity labels. C-04's new `permission` and `role_permission` tables define what each role can DO — authorization rules. This clean separation means C-02 stays untouched while C-04 builds the permission layer on top.

C-04 **retrofits** all existing C-01 and C-02 endpoints with authorization checks. Every endpoint that creates, reads, updates, or deletes resources must declare its required permission via a single FastAPI dependency `require_permission(resource, action, ...)` that each endpoint opts into.

This is the **second cross-domain change** in the repo. C-04 modifies both C-01's and C-02's behavioral contracts: all endpoints now enforce authorization via `require_permission`. C-04 also adds a `platform_owner` row to C-02's `role` table. The change contains three delta specs: `authorization` (ADDED), `tenant-institution` (MODIFIED), and `identity-user-management` (MODIFIED).

## What Changes

- **NEW: `permission` table** — Global lookup table cataloging all Phase 1 permissions (26 rows: 14 C-01 + 12 C-02). Columns: `id` (UUID PK), `name` (unique), `description`, `resource`, `action`. No RLS (global data). Seeded in migration 004.
- **NEW: `role_permission` table** — Mapping table linking C-02's `role` rows to `permission` rows (FK to `role.id`). ~40 seed rows defining what each of the 7 C-02 roles can do. All C-02 permissions use `institution` Casbin scope. No RLS (global data).
- **NEW: `platform_owner` role row** — A new row in C-02's `role` table (added by C-04 migration). Assigned to the platform owner user via `role_assignment`. C-04's `role_permission` does NOT map this role — it receives `*.*` from C-01's existing D11 Casbin policies.
- **NEW: Central Casbin enforcer** — App factory creates exactly one Casbin enforcer from the model at `kernel/authz/casbin_model.conf` (moved from C-01). Calls `register_casbin_policies(enforcer)` on each module manifest in dependency order (C-01 → C-02 → C-03 → C-04). Enforcer available via `get_enforcer()` FastAPI dependency.
- **NEW: `require_permission` FastAPI dependency** — Each endpoint opts in via `Depends(require_permission(resource, action, client_id=..., institution_id=..., owner_id=...))`. Reads `TenantContext.roles`, builds Casbin subject/object, calls `enforcer.enforce()`. Two-step enforcement: Casbin for role+scope; app-level for ownership.
- **NEW: C-04 `register_casbin_policies(enforcer)` hook** — `on_startup` reads `role_permission` from DB into in-memory dict. `register_casbin_policies` adds Casbin policies and role groupings. Policies are in-memory at runtime.
- **NEW: Permission ORM models** — `Permission` and `RolePermission` SQLAlchemy models for migration autogenerate + startup loader. No repository (D23). No CRUD API (Phase 2).
- **MODIFIED: C-01 Casbin model relocation** — `casbin_model.conf` moves from `business/tenant_institution/` to `kernel/authz/`. C-01's `build_enforcer()` is removed. C-01's `register_casbin_policies(enforcer)` hook continues to add D11 policies using the relocated model.
- **MODIFIED: C-01 endpoint retrofit** — All ~15 C-01 endpoints gain `Depends(require_permission(resource, action, client_id=..., institution_id=...))`. Endpoints now return 403 if the calling user's role lacks the required permission or if scope checks fail.
- **MODIFIED: C-02 endpoint retrofit** — All ~12 C-02 endpoints gain `Depends(require_permission(resource, action, ...))`. Profile read/update endpoints use `owner_id` for ownership checks. Lookup endpoints (user_category, role list) also require authorization.
- **MODIFIED: App factory** — `kernel/app_factory.py` gains enforcer creation + policy registration iteration. Same pattern as route registration.
- **MODIFIED: C-01/C-02 test fixtures** — Tests must include `role` + `permission` + `role_permission` seed data or override `get_enforcer()` dependency.

## Capabilities

### New Capabilities
- `authorization`: Centralized authorization — `permission` catalog, `role_permission` mapping, Casbin enforcer singleton, `require_permission` dependency, ownership enforcement, `platform_owner` role row.

### Modified Capabilities
- `tenant-institution`: C-01's Casbin model relocated. All C-01 endpoints now require authorization. `build_enforcer()` removed. C-01 tests adapted.
- `identity-user-management`: All C-02 endpoints now require authorization. `platform_owner` row added to C-02's `role` table. C-02 tests adapted.

## Impact

- **New code:** `backend/kernel/authz/` (manifest, models, dependencies, services, `casbin_model.conf`)
- **New migration:** `004_c04_authorization.py` — `permission` table (26 seed rows), `role_permission` table (~40 seed rows), `platform_owner` row in C-02's `role` table
- **Modified code:** All C-01 route files (~15 endpoints), all C-02 route files (~12 endpoints)
- **Modified code:** `kernel/app_factory.py` — enforcer creation + policy registration
- **Modified code:** `tests/conftest.py` — enforcer fixture, permission seed data
- **Removed code:** C-01's `build_enforcer()` function
- **Relocated code:** `casbin_model.conf` from `business/tenant_institution/` to `kernel/authz/`
- **Kernel dependencies:** C-04 inherits TenantContext, TenantAwareRepositoryBase from kernel; depends on C-02's `role` table via FK
- **Future consumers:** All future business modules (C-05 attendance, C-06 homework, etc.) will define their own permissions and register them via `register_casbin_policies`. C-11 (Audit) receives access denial events.
- **Boundary declarations:** C-04 does NOT own user identity (C-02), authentication (C-03), role identity labels (C-02's `role` table), audit storage (C-11), or the frontend permission UI (deferred to Phase 2).
