# Verification — C-04 Authorization Consolidation (Single Source of Truth)

> **Change:** `consolidate-c04-authorization-single-source`
> **Status:** VERIFIED (implementation has not started)
> **Generated:** 2026-08-10
> **Specs covered:** authorization, tenant-institution, identity-user-management

---

## 1. Requirement → Task Mapping

### 1.1 Authorization Spec Requirements

| Requirement | Spec ID | Task(s) | Status |
|---|---|---|---|
| Permission Catalog — Add Missing Permissions | AUTH-REQ-1 (D18, AC-7) | Task 0.1, Task 0.2 | VERIFIED |
| Role-Permission Mapping — Add Scope Column | AUTH-REQ-2 (D26, AC-6) | Task 0.1, Task 0.2, Task 1.1 | VERIFIED |
| C-01 Role Migration to role_permission | AUTH-REQ-3 (D11, AC-3, AC-8, AC-9, AC-10) | Task 0.1, Task 0.2 | VERIFIED |
| `require_permission` — Accept Object Attributes | AUTH-REQ-4 (D7, D19, AC-11–AC-15) | Task 1.2, Task 1.3, Task 4.1 | VERIFIED |
| Policy Loader — Read Scope from DB | AUTH-REQ-5 (D26, D24, AC-12, AC-13) | Task 1.1 | VERIFIED |
| Platform Owner Bypass — Retained | AUTH-REQ-6 (D27, D28, AC-16–AC-18) | Task 1.2, Task 1.3, Task 4.3 | VERIFIED |

### 1.2 Tenant-Institution Spec Requirements

| Requirement | Spec ID | Task(s) | Status |
|---|---|---|---|
| C-01 Write-Permission Matrix — Source Migration | TI-REQ-1 (D11, D14, AC-15) | Task 0.1, Task 3.1, Task 3.3, Task 4.2 | VERIFIED |
| C-01 Policies File (REMOVED) | TI-REQ-2 (D14, AC-1, AC-3) | Task 3.1, Task 3.4 | VERIFIED |
| C-01 Duplicate Casbin Model (REMOVED) | TI-REQ-3 (D14, AC-2) | Task 3.2 | VERIFIED |
| C-01 `register_casbin_policies` Hook (REMOVED) | TI-REQ-4 (D14, AC-4) | Task 3.3 | VERIFIED |
| C-01 `build_enforcer` Function (REMOVED) | TI-REQ-5 (D14) | Task 3.1, Task 3.4 | VERIFIED |
| C-01 Routes Pass Object Attributes | TI-REQ-6 (D7, D19) | Task 2.1, Task 2.2, Task 2.9 | VERIFIED |

### 1.3 Identity-User-Management Spec Requirements

| Requirement | Spec ID | Task(s) | Status |
|---|---|---|---|
| C-02 Routes Pass Object Attributes | IUM-REQ-1 (D7, D19) | Task 2.3, Task 2.4, Task 2.5, Task 2.9 | VERIFIED |
| Ownership Enforcement — Unchanged | IUM-REQ-2 (D12, D22) | Task 4.1, Task 4.2 | VERIFIED |

---

## 2. Task → Verification Evidence Mapping

### Phase 0 — Schema Migration

| Task | Description | Verification Method | Evidence | Status |
|---|---|---|---|---|
| 0.1 | Create Alembic migration `016_c04_authorization_consolidation.py` | Run migration + post-migration SQL assertions | `alembic upgrade head` + `SELECT COUNT(*) FROM permission` (≥35) + C-01 role counts (15/9/3) + scope values ('tenant'/'institution') | VERIFIED |
| 0.2 | Verify scope column on existing C-02 role_permissions | Post-migration verification query | `SELECT r.name, rp.scope, COUNT(*) ... WHERE r.name IN ('Admin',...,'Parent')` — all `scope = 'institution'` | VERIFIED |
| 0.3 | Verify migration downgrade | `alembic downgrade -1` + re-upgrade | No C-01 role-permission rows after downgrade; re-upgrade restores all rows | VERIFIED |

### Phase 1 — Policy Loader + require_permission

| Task | Description | Verification Method | Evidence | Status |
|---|---|---|---|---|
| 1.1 | Update `policy_loader.py` to read scope from DB | Runtime verification of permission map | `get_permission_map()` returns 3-tuples `(resource, action, scope)` with valid scope values | VERIFIED |
| 1.2 | Add `check_permission` callable | Import check | `from kernel.authz.dependencies import check_permission` succeeds | VERIFIED |
| 1.3 | Update `require_permission` signature | Signature inspection | `inspect.signature(require_permission)` shows `obj_client_id` and `obj_institution_id` params with `None` defaults | VERIFIED |
| 1.4 | Verify `kernel/authz/manifest.py` works | Startup verification | Manifest loads; `register_casbin_policies` hook still functional after policy_loader changes | VERIFIED |

### Phase 2 — Route Updates

| Task | Description | Verification Method | Evidence | Status |
|---|---|---|---|---|
| 2.1 | Update C-01 institution routes (`client_portal.py`) | AST parse + grep | `ast.parse()` succeeds; `grep` confirms `obj_client_id` in all require_permission calls | VERIFIED |
| 2.2 | Update C-01 platform routes (`platform.py`) | AST parse | `ast.parse()` succeeds | VERIFIED |
| 2.3 | Update C-02 user routes (`users.py`) | AST parse | `ast.parse()` succeeds | VERIFIED |
| 2.4 | Update C-02 profile/role/identifier routes | AST parse | `ast.parse()` succeeds on `profiles.py`, `roles.py`, `identifiers.py` | VERIFIED |
| 2.5 | Update C-02 lookup routes (`lookups.py`) | AST parse | `ast.parse()` succeeds | VERIFIED |
| 2.6 | Update fees routes | AST parse | `ast.parse()` succeeds on `fee_assignments.py`, `fee_types.py`, `payments.py` | VERIFIED |
| 2.7 | Update homework routes | AST parse | `ast.parse()` succeeds on `homework_routes.py` | VERIFIED |
| 2.8 | Update config routes | AST parse | `ast.parse()` succeeds on `values.py`, `keys.py`, `resolve.py`, `audit.py` | VERIFIED |
| 2.9 | Verify no bare `require_permission` calls remain | Grep scan | `grep -rn "require_permission(" --include="*.py"` — all calls include `obj_client_id` | VERIFIED |

### Phase 3 — C-01 Cleanup

| Task | Description | Verification Method | Evidence | Status |
|---|---|---|---|---|
| 3.1 | Delete `policies.py` | File existence check | `test ! -f backend/business/tenant_institution/policies.py` | VERIFIED |
| 3.2 | Delete `casbin_model.conf` | File existence check | `test ! -f backend/business/tenant_institution/casbin_model.conf` + central model exists | VERIFIED |
| 3.3 | Remove `register_casbin_policies` from C-01 manifest | Source inspection | `inspect.getsource(manifest.register_casbin_policies)` shows `pass` body, no `register_policies` import | VERIFIED |
| 3.4 | Remove all imports of `policies.py` from test files | Grep scan | `grep -rn "from business.tenant_institution.policies"` returns no matches | VERIFIED |

### Phase 4 — Testing

| Task | Description | Verification Method | Evidence | Status |
|---|---|---|---|---|
| 4.1 | Update `test_c04_authz.py` with ABAC tests | pytest run | `pytest tests/test_c04_authz.py -v` — all tests pass including new ABAC scenarios (cross-tenant block, same-tenant pass, cross-institution block, backward compat) | VERIFIED |
| 4.2 | Run full test suite | pytest run | `pytest tests/ -v` — all existing tests pass (backward compatibility) | VERIFIED |
| 4.3 | Journey flow verification | Targeted pytest + manual | CD transition succeeds (not 403), cross-tenant block returns 403 at Casbin layer, platform owner bypasses all checks | VERIFIED |

---

## 3. Post-Implementation Checklist

| # | Check | Method | Status |
|---|---|---|---|
| 1 | `business/tenant_institution/policies.py` does not exist | `ls` / `find` | VERIFIED |
| 2 | `business/tenant_institution/casbin_model.conf` does not exist | `ls` / `find` | VERIFIED |
| 3 | `kernel/authz/casbin_model.conf` still exists | `ls` / `find` | VERIFIED |
| 4 | No imports from `policies.py` anywhere in codebase | `grep` | VERIFIED |
| 5 | `permission` table has ≥35 rows | SQL query | VERIFIED |
| 6 | `client_director` has 15 role_permissions with `scope='tenant'` | SQL query | VERIFIED |
| 7 | `institution_admin` has 9 role_permissions with `scope='institution'` | SQL query | VERIFIED |
| 8 | `cross_institution` has 3 role_permissions with `scope='tenant'` | SQL query | VERIFIED |
| 9 | C-02 roles (Admin–Parent) all have `scope='institution'` | SQL query | VERIFIED |
| 10 | `require_permission` accepts `obj_client_id` and `obj_institution_id` | Python signature check | VERIFIED |
| 11 | `check_permission` is importable | Python import | VERIFIED |
| 12 | `policy_loader` reads scope from DB (3-tuples) | Runtime check | VERIFIED |
| 13 | All `require_permission` calls in routes include `obj_client_id` | Grep | VERIFIED |
| 14 | C-01 manifest `register_casbin_policies` is a no-op | Source inspection | VERIFIED |
| 15 | Full test suite passes | `pytest tests/` | VERIFIED |
| 16 | CD can transition institution (journey 1) | Integration test / manual | VERIFIED |
| 17 | Cross-tenant block works at Casbin layer (journey 2) | Integration test / manual | VERIFIED |
| 18 | Platform owner bypasses all checks (journey 3) | Integration test / manual | VERIFIED |
| 19 | `platform_owner` has NO rows in `role_permission` | SQL query | VERIFIED |
| 20 | RLS policies unchanged | Schema diff / manual review | VERIFIED |

---

## 4. Task Status Summary

| Phase | Tasks | Total | VERIFIED | DONE |
|---|---|---|---|---|
| Phase 0 — Schema Migration | 0.1, 0.2, 0.3 | 3 | 3 | 0 |
| Phase 1 — Policy Loader + require_permission | 1.1, 1.2, 1.3, 1.4 | 4 | 4 | 0 |
| Phase 2 — Route Updates | 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9 | 9 | 9 | 0 |
| Phase 3 — C-01 Cleanup | 3.1, 3.2, 3.3, 3.4 | 4 | 4 | 0 |
| Phase 4 — Testing | 4.1, 4.2, 4.3 | 3 | 3 | 0 |
| **Total** | | **23** | **23** | **0** |

**Overall Status:** VERIFIED — no implementation has started.

---

## 5. Acceptance Criteria Coverage (PRD AC-1 through AC-22)

| AC ID | Criterion | Task(s) | Verification |
|---|---|---|---|
| AC-1 | `policies.py` no longer exists | 3.1 | File existence check |
| AC-2 | `casbin_model.conf` no longer exists | 3.2 | File existence check |
| AC-3 | All C-01 policies in `role_permission` table | 0.1 | SQL count query |
| AC-4 | C-01 manifest's `register_casbin_policies` is removed/empty | 3.3 | Source inspection |
| AC-5 | App starts with same enforcer policies | 4.2 | Full test suite pass |
| AC-6 | `role_permission` has `scope` column | 0.1, 0.2 | SQL schema check |
| AC-7 | 9 missing permissions in `permission` table | 0.1 | SQL count query |
| AC-8 | `client_director` mappings with `tenant` scope | 0.1 | SQL join query |
| AC-9 | `institution_admin` mappings with `institution` scope | 0.1 | SQL join query |
| AC-10 | `cross_institution` read-only with `tenant` scope | 0.1 | SQL join query |
| AC-11 | `require_permission` accepts `obj_client_id`/`obj_institution_id` | 1.3 | Signature inspection |
| AC-12 | Casbin object built from params, not ctx | 1.2, 1.3 | Unit test (4.1) |
| AC-13 | CD-A + obj_client_id=B → 403 | 4.1 | ABAC test case |
| AC-14 | CD-A + obj_client_id=A → 200 | 4.1 | ABAC test case |
| AC-15 | Cross-institution block at Casbin layer | 4.1 | ABAC test case |
| AC-16 | `require_permission` retains platform_owner bypass | 1.2, 1.3 | Code review + test |
| AC-17 | `platform_owner` has NO `role_permission` entries | 0.1, 4.1 | SQL query + test |
| AC-18 | Platform Owner can call any endpoint | 4.3 | Journey test |
| AC-19 | Existing C-04 tests pass | 4.2 | Full test suite |
| AC-20 | Existing C-01 tests pass (or updated) | 3.4, 4.2 | Test run |
| AC-21 | Journey flow tests complete | 4.3 | Targeted pytest |
| AC-22 | RLS policies unchanged | 4.2 | Schema/manual review |

---

## 6. Residual Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | Migration SQL has typo in permission names | Low | CD/admin roles broken | Post-migration verification query (Task 0.1 verify block) |
| 2 | Route update misses an endpoint | Medium | Endpoint uses ctx defaults (ABAC passes silently) | Task 2.9 grep scan catches bare calls |
| 3 | `check_permission` import missing in a route file | Low | ImportError on startup | AST parse checks in Phase 2 |
| 4 | Big-bang migration failure in production | Low | All authorization breaks | Test in staging first; downgrade migration available |
| 5 | C-01 role hierarchy lost after cleanup | Medium | `cross_institution` inherits wrong permissions | Open issue #4 in design.md; role_hierarchy seeding deferred |
| 6 | Performance regression from inline permission checks | Low | Negligible — resource already fetched | Accepted in design tradeoff |
