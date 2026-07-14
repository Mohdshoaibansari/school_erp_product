# Implementation Tasks — C-04 Authorization

> **Traceability.** Each task traces to grill-me decision IDs (D1–D33) and PRD AC IDs (AC-1..AC-24). Tasks are grouped by concern and ordered by dependency. This is a checklist for the apply phase — no implementation is performed here.
>
> **Stack & architecture note.** The platform tech-stack ADR locks the stack (Postgres+Supabase, Python+FastAPI, SQLAlchemy 2.0+Alembic, Casbin RBAC+ABAC, pytest). The platform software-architecture ADR locks the modular-monolith + module-manifest + monorepo structure (A1–A11). C-04 follows C-01/C-02/C-03's established patterns exactly.
>
> **Cross-domain note.** This is the second cross-domain change. Tasks include both C-04 ADDED tasks and C-01/C-02 MODIFIED tasks (endpoint retrofit + Casbin model relocation). C-01 modification tasks are in §14; C-02 modification tasks are in §15.
>
> **References:** proposal.md, specs/authorization/spec.md, specs/tenant-institution/spec.md, specs/identity-user-management/spec.md, design.md; PRD `docs/prd/c-04-authorization.md`; C-01 policies `business/tenant_institution/policies.py`; C-02 role table `kernel/user/models/role.py`.

## 1. Module structure & manifest (A5, D9, AC-20, AC-21)

> C-04 is a kernel-tier module (A2). It registers via the ModuleManifest Protocol (A5). The manifest hooks are invoked by the app factory in dependency order (after C-03).

- [ ] 1.1 Create the C-04 module directory structure under `/backend/kernel/authz/` with `__init__.py`, `manifest.py`, `casbin_model.conf`, `models/` (with `__init__.py`, `permission.py`), `dependencies.py`, `services/` (with `__init__.py`, `policy_loader.py`). — evidence: directory structure exists; `__init__.py` files importable.
- [ ] 1.2 Implement `AuthorizationManifest` (subclass of `ManifestBase`) with `register_routes` (empty), `register_casbin_policies`, `on_startup` hooks. Create a `manifest` singleton. — evidence: `manifest.py` exists; `manifest` object importable.
- [ ] 1.3 Register C-04 manifest in the app factory's module list (after C-03, in dependency order). — evidence: `test_app_boots_with_c04_manifest` passes.

## 2. Casbin model relocation (D4, D14, D25, AC-17)

> The model file moves from C-01 to C-04. No content changes to the model.

- [ ] 2.1 Copy `business/tenant_institution/casbin_model.conf` to `kernel/authz/casbin_model.conf`. — evidence: file exists at `kernel/authz/casbin_model.conf`; content identical to original.
- [ ] 2.2 Update all references to the model path in C-01's `policies.py` and tests to point to `kernel/authz/casbin_model.conf`. — evidence: `test_casbin_permissions.py` uses the new path; `policies.py` references updated.

## 3. Database schema — permission + role_permission (D8, D18, D30, AC-1, AC-2, AC-3) — Alembic migration `004_c04_authorization.py`

> All C-04 migrations live in the single Alembic env at `/backend/migrations/` (A7) under filenames prefixed `004_c04_*`.

- [ ] 3.1 Create the `permission` table (`id` UUID v4 PK, `name` TEXT UNIQUE NOT NULL, `description` TEXT, `resource` TEXT NOT NULL, `action` TEXT NOT NULL, `created_at` TIMESTAMPTZ NOT NULL DEFAULT now()). No RLS (global data). — evidence: migration creates `permission` table; `test_permission_pk_is_uuid_v4` + `test_permission_has_no_rls` pass.
- [ ] 3.2 Seed 26 permission rows — 14 C-01 + 12 C-02 as enumerated in the spec. — evidence: migration inserts 26 rows; `test_permission_26_rows_seeded` passes.
- [ ] 3.3 Create the `role_permission` table (`id` UUID v4 PK, `role_id` UUID FK → role, `permission_id` UUID FK → permission, UNIQUE(role_id, permission_id)). No RLS (global data). — evidence: migration creates `role_permission` table; `test_role_permission_has_fk_to_role` + `test_role_permission_has_no_rls` pass.
- [ ] 3.4 Seed ~40 role_permission rows — mapping each of the 7 C-02 roles to their permissions per §2.1.2 of the PRD. — evidence: migration inserts ~40 rows; `test_role_permission_mapping_admin_has_user_create` + `test_role_permission_mapping_teacher_lacks_user_create` pass.
- [ ] 3.5 Insert `platform_owner` row into C-02's `role` table — `INSERT INTO role (id, name) VALUES (gen_random_uuid(), 'platform_owner') ON CONFLICT (name) DO NOTHING`. — evidence: migration inserts the row; `test_platform_owner_role_exists` passes.

## 4. Permission ORM models (D23, AC-1, AC-2)

> ORM models for Alembic autogenerate and startup loader. No repository (D23).

- [ ] 4.1 Implement `Permission` ORM model at `models/permission.py` — columns: `id`, `name`, `description`, `resource`, `action`, `created_at`. — evidence: `models/permission.py` exists; model importable; `test_permission_model_fields` passes.
- [ ] 4.2 Implement `RolePermission` ORM model at `models/permission.py` — columns: `id`, `role_id` (FK to C-02's Role), `permission_id` (FK to Permission), unique constraint. — evidence: model importable; `test_role_permission_model_fk` passes.

## 5. Casbin enforcer singleton (D10, D29, AC-11)

> Enforcer created by app factory, injected via `get_enforcer()` dependency.

- [ ] 5.1 Extend `kernel/app_factory.py` to create a Casbin enforcer from `kernel/authz/casbin_model.conf` after loading manifests, iterate manifests calling `register_casbin_policies(enforcer)` in dependency order, and store the enforcer singleton. — evidence: `test_app_factory_creates_enforcer` + `test_app_factory_calls_register_casbin_policies_in_order` pass.
- [ ] 5.2 Implement `get_enforcer()` dependency in `kernel/authz/dependencies.py` — returns the global singleton. — evidence: `test_get_enforcer_returns_same_instance` passes.

## 6. C-04 policy loader (D11, D24, D29, AC-12, AC-13)

> `on_startup` reads DB; `register_casbin_policies` adds to enforcer.

- [ ] 6.1 Implement `load_permission_map(session)` in `services/policy_loader.py` — reads all `role_permission` rows joined with `role` and `permission`, stores into an in-memory dict `{role_name: [(resource, action), ...]}`. — evidence: `test_load_permission_map_populates_dict` passes.
- [ ] 6.2 Implement `register_casbin_policies(enforcer)` in `services/policy_loader.py` — iterates the in-memory dict, calls `enforcer.add_policy(role, resource, action, "institution")` and `enforcer.add_grouping_policy(role, casbin_label)`. — evidence: `test_register_casbin_policies_adds_policies_to_enforcer` passes.
- [ ] 6.3 Wire `on_startup` in the manifest to call `load_permission_map(session)`. — evidence: `test_on_startup_loads_permission_map` passes.
- [ ] 6.4 Wire `register_casbin_policies(enforcer)` in the manifest to call the policy_loader. — evidence: `test_manifest_register_casbin_policies` passes.

## 7. `require_permission` dependency (D5, D7, D12, D13, D19, D22, D31, AC-4 through AC-10)

> FastAPI dependency at `kernel/authz/dependencies.py`.

- [ ] 7.1 Implement `require_permission(resource, action, client_id=None, institution_id=None, owner_id=None)` — returns a FastAPI dependency closure that reads `TenantContext.roles`, builds Casbin subject/object, calls `enforcer.enforce()`, raises 403 on deny. — evidence: `test_require_permission_function_signature` passes.
- [ ] 7.2 Implement Step 1 (Casbin role+scope check) — build subject from TenantContext (`{role, client_id, institution_id}`), build object from params (`{name, client_id, institution_id}`), call `enforcer.enforce(sub, obj, action)`. — evidence: `test_require_permission_granted` + `test_require_permission_denied_wrong_role` + `test_require_permission_denied_cross_institution` pass.
- [ ] 7.3 Implement Step 2 (ownership check) — if `owner_id` provided and doesn't match `ctx.user_id`, perform admin bypass check. If the user's role has `institution` scope via Casbin → allow; else → 403. — evidence: `test_require_permission_ownership_allowed_own` + `test_require_permission_ownership_denied_other` + `test_require_permission_ownership_admin_bypass` pass.
- [ ] 7.4 Handle edge cases: no roles (empty list), platform_owner role (should pass all), null client_id/institution_id. — evidence: `test_require_permission_no_roles` + `test_require_permission_platform_owner_bypass` + `test_require_permission_null_ids` pass.

## 8. C-01 Casbin policies update (D14, AC-16)

> C-01's policies.py and tests adapted for relocated model and centralized enforcer.

- [ ] 8.1 Update `business/tenant_institution/policies.py` — remove `build_enforcer()` function; update `casbin_model_path()` to point to `kernel/authz/casbin_model.conf`. — evidence: `build_enforcer` no longer exists; `casbin_model_path()` returns new path.
- [ ] 8.2 Update C-01's `register_casbin_policies(enforcer)` hook in the manifest — ensure it still calls `register_policies(enforcer)` from policies.py. — evidence: C-01 manifest unchanged; `register_casbin_policies` calls through as before.
- [ ] 8.3 Update C-01's Casbin tests (`test_casbin_permissions.py`) — create enforcer from relocated model, call `register_policies(enforcer)`, test enforcement. — evidence: 12 C-01 Casbin tests pass with relocated model.

## 9. C-01 endpoint retrofit (D16, D19, D20, AC-14)

> Every C-01 endpoint gains `Depends(require_permission(...))`.

- [ ] 9.1 Retrofit `routes/client_portal.py` — `GET /institutions`, `POST /institutions`, `GET /institutions/{id}`, `PUT /institutions/{id}`, `POST /institutions/{id}/transition-lifecycle`. — evidence: each endpoint has `Depends(require_permission(resource, action, ...))`; `test_c01_institution_endpoints_have_permission` passes.
- [ ] 9.2 Retrofit `routes/platform.py` — `GET /clients`, `POST /clients`, `PUT /clients/{id}`, `POST /clients/{id}/transition-lifecycle`, `POST /clients/{id}/transfer-ownership`, and org_unit endpoints. — evidence: each endpoint has permission dependency.
- [ ] 9.3 Retrofit org_unit routes in `routes/platform.py` — `GET /org-units`, `POST /org-units`, `GET /org-units/{id}`, `PUT /org-units/{id}`, `DELETE /org-units/{id}`, `POST /org-units/{id}/move`. — evidence: each endpoint has `Depends(require_permission("org_unit", action, ...))`.
- [ ] 9.4 Retrofit institution_type lookup — `GET /institution-types`. — evidence: endpoint has `Depends(require_permission("institution_type", "read", ...))`.

## 10. C-02 endpoint retrofit (D16, D22, D31, AC-15)

> Every C-02 endpoint gains `Depends(require_permission(...))`. Profile endpoints use `owner_id`.

- [ ] 10.1 Retrofit `routes/users.py` — `GET /users`, `POST /users`, `GET /users/{user_id}`, `PUT /users/{user_id}`, `POST /users/{user_id}/transition`. Profile read/update pass `owner_id=user_id` for ownership check. — evidence: each endpoint has permission dependency; `test_c02_user_endpoints_have_permission` passes.
- [ ] 10.2 Retrofit `routes/profiles.py` — `POST /users/{user_id}/profile`, `GET /users/{user_id}/profile`, `PUT /users/{user_id}/profile`. — evidence: each endpoint has `Depends(require_permission("user_profile", action, ...))`.
- [ ] 10.3 Retrofit `routes/roles.py` — `GET /users/{user_id}/roles`, `POST /users/{user_id}/roles`, `DELETE /users/{user_id}/roles/{assignment_id}`. — evidence: each endpoint has `Depends(require_permission("role_assignment", action, ...))`.
- [ ] 10.4 Retrofit `routes/identifiers.py` — `GET /users/{user_id}/identifiers`, `POST /users/{user_id}/identifiers`, `DELETE /users/{user_id}/identifiers/{identifier_id}`. — evidence: each endpoint has `Depends(require_permission("user_identifier", action, ...))`.
- [ ] 10.5 Retrofit `routes/lookups.py` — `GET /user-categories`, `GET /roles`. — evidence: `user-categories` has `Depends(require_permission("user", "read", ...))`; `roles` has `Depends(require_permission("role_assignment", "read", ...))`.

## 11. Test fixtures update (D17, D20, AC-22 through AC-24)

> C-01/C-02 existing tests must pass after retrofit. C-04 tests use real Casbin.

- [ ] 11.1 Create C-04 test conftest — `kernel/authz/conftest.py` with fixtures: `seed_permissions(session)` (creates 26 permission rows), `seed_role_permissions(session)` (creates mappings), `seed_roles(session)` (ensures 7 C-02 roles + platform_owner exist), `casbin_enforcer` (builds enforcer with seed data). — evidence: fixtures are importable and functional.
- [ ] 11.2 Add permission seed data to the existing test conftest — `tests/conftest.py` gains fixtures or setup that seeds `permission` + `role_permission` rows before C-01/C-02 tests run, OR provides `app.dependency_overrides[get_enforcer]` for bypass. — evidence: existing C-01 and C-02 tests pass without modification.
- [ ] 11.3 Update `tests/conftest.py` `app` fixture — register C-04 manifest in `create_app()`. — evidence: app boots with C-04 manifest registered.

## 12. C-04 unit tests — Casbin enforcement (D17, AC-22)

> Real Casbin enforcer with seed policies. Test each role's allowed and denied permissions.

- [ ] 12.1 Test Admin role permissions — assert Admin can `user.create`, `user.suspend`, `institution.read`, `org_unit.create`; cannot `client.create`. — evidence: `test_admin_casbin_permissions` passes.
- [ ] 12.2 Test Principal role permissions — assert Principal can `institution.read`, `org_unit.read`; cannot `user.create`, `user.suspend`. — evidence: `test_principal_casbin_permissions` passes.
- [ ] 12.3 Test Teacher role permissions — assert Teacher can `user.read`, `user.update` (own); cannot `user.create`, `institution.read`, `org_unit.create`. — evidence: `test_teacher_casbin_permissions` passes.
- [ ] 12.4 Test Student/Parent/Staff roles — minimal permissions (read own profile only). — evidence: `test_student_casbin_permissions`, `test_parent_casbin_permissions`, `test_staff_casbin_permissions` pass.
- [ ] 12.5 Test scope enforcement — same role, different institution_id → deny. Cross-institution. Cross-tenant. — evidence: `test_scope_institution_enforced`, `test_scope_tenant_enforced` pass.
- [ ] 12.6 Test platform_owner bypass — `*.*` at `any` scope. — evidence: `test_platform_owner_bypass` passes.

## 13. C-04 integration tests — `require_permission` dependency (D17, AC-23)

> Test the dependency in isolation with a known TenantContext.

- [ ] 13.1 Test `require_permission` grants access to authorized role — Admin with user.create at matching institution. — evidence: `test_dependency_granted_admin_user_create` passes.
- [ ] 13.2 Test `require_permission` denies unauthorized role — Teacher with user.create. — evidence: `test_dependency_denied_teacher_user_create` passes.
- [ ] 13.3 Test `require_permission` denies cross-institution — Admin at School A reading institution at School B. — evidence: `test_dependency_denied_cross_institution` passes.
- [ ] 13.4 Test `require_permission` ownership — Teacher reads own profile (allowed), Teacher reads other profile (denied), Admin reads other profile (allowed). — evidence: `test_dependency_ownership_own`, `test_dependency_ownership_other_denied`, `test_dependency_ownership_admin_bypass` pass.
- [ ] 13.5 Test `require_permission` platform_owner bypasses all. — evidence: `test_dependency_platform_owner_bypass` passes.

## 14. C-01 retrofit tests (D16, D20, AC-14, AC-24)

> Existing C-01 tests must pass with retrofitted authorization.

- [ ] 14.1 Verify all C-01 existing tests pass after retrofit — full test suite. — evidence: `uv run python -m pytest tests/ -k "test_c01 or test_casbin"` passes.
- [ ] 14.2 Verify C-01 Casbin tests pass with relocated model — `test_casbin_permissions.py`. — evidence: 12 tests pass with `kernel/authz/casbin_model.conf`.

## 15. C-02 retrofit tests (D16, D20, AC-15, AC-24)

> Existing C-02 tests must pass with retrofitted authorization.

- [ ] 15.1 Verify all C-02 existing tests pass after retrofit — full C-02 test suite. — evidence: `uv run python -m pytest tests/test_c02_user.py` passes.
- [ ] 15.2 Verify C-03 existing tests pass after retrofit — C-03 should be unaffected. — evidence: `uv run python -m pytest tests/test_c03_auth.py` passes.

## 16. Import-linter and boundary checks (D32, AC-20, AC-21)

- [ ] 16.1 Run import-linter — A3 (`kernel → ∅`) and A4 (acyclic) must keep. — evidence: `uv run lint-imports` shows "2 kept, 0 broken".
- [ ] 16.2 Verify `kernel/authz/` has no imports from `business/` or `shared/`. — evidence: manual grep or linter contract confirms.
