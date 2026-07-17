# Fees Module — Impact Classification

> **Date:** 2026-07-14  
> **PRD:** `docs/prd/fees-module.md`

---

## Summary

The Fees module is a **NEW business domain** at `backend/business/fees/`. It is the first business module built on the completed platform foundation. Impact classification:

| Classification | Domain | What |
|---|---|---|
| **ADDED** | `fees` | New business module — 3 entities, ~13 endpoints, audit events, Casbin policies |
| **MODIFIED** | `authorization` (C-04) | 11 new permission rows + ~17 role_permission rows in C-04's tables |
| **MODIFIED** | N/A | Test conftest — register fees manifest in app fixture |

---

## ADDED: `fees` domain

### New module: `backend/business/fees/`

| Component | Description |
|---|---|
| `manifest.py` | ModuleManifest with `register_routes`, `register_casbin_policies` (empty), `on_startup` |
| `models/` | FeeType, FeeAssignment, Payment ORM models |
| `repos/` | FeeTypeRepository, FeeAssignmentRepository, PaymentRepository (all inherit TenantAwareRepositoryBase) |
| `services/` | FeesService (CRUD + payment recording + status updates + receipt generation) |
| `routes/` | fee_types.py, fee_assignments.py, payments.py |
| `dependencies.py` | get_fees_service() |
| `policies.py` | (optional — permissions via C-04 migration per D8) |

### New migration: `005_fees_module.py`

Creates 3 tables:
- `fee_type` (with RLS)
- `fee_assignment` (with RLS)
- `payment` (with RLS)

Adds to C-04 tables:
- 11 new `permission` rows (ON CONFLICT DO NOTHING)
- ~17 new `role_permission` rows (ON CONFLICT DO NOTHING)

### New tests: `tests/test_fees.py`

- Unit tests for service logic
- Integration tests for endpoints
- Authorization tests (role-based access)
- Ownership tests (student sees only own fees)

### New audit events

5 event types emitted via C-11 AuditEmitter Protocol.

---

## MODIFIED: `authorization` domain (C-04)

### What changes

The fees migration `005_fees_module.py` inserts rows into C-04's `permission` and `role_permission` tables:

```sql
-- 11 new permission rows
INSERT INTO permission (id, name, description, resource, action) VALUES
(... 'fee.read', ...),
(... 'fee.create', ...),
... etc.

-- ~17 new role_permission rows
INSERT INTO role_permission (role_id, permission_id) ...
```

### Impact

- C-04's `on_startup` auto-loads new rows at next restart — **no C-04 code change needed**.
- C-04's `permission` table grows from 26 to 37 rows.
- C-04's `role_permission` table grows from ~40 to ~57 rows.
- No DDL changes to C-04 tables (only INSERTs).
- C-04 tests unaffected (new rows don't break existing role mappings).

### C-04 manifest registration

Fees manifest's `register_casbin_policies(enforcer)` is **empty** — all policies are in the DB, loaded by C-04.

---

## NOT MODIFIED: other domains

| Domain | Status | Reason |
|---|---|---|
| C-01 (tenant-institution) | No change | Consumed via TenantContext, TenantAwareRepositoryBase — no endpoint changes |
| C-02 (identity-user-management) | No change | Consumed via app_user FK, user_category validation — no endpoint changes |
| C-03 (authentication) | No change | Consumed via JWT authentication — no changes |
| C-11 (audit) | No change | Consumed via AuditEmitter Protocol — no changes |

---

## Test fixture impact

`tests/conftest.py` `app` fixture:
- Add `from business.fees.manifest import manifest as fees_manifest`
- Update `create_app([..., fees_manifest])`
- `AlwaysAllowEnforcer` override already handles new permissions

---

## Import-linter impact

- `business/fees/` imports from `kernel/` (TenantAwareRepositoryBase, TenantContext, require_permission, AuditEmitter) — allowed (business → kernel).
- `business/fees/` imports from `kernel/authz/` (require_permission) — allowed (business → kernel).
- No `business/fees/` → `shared/` imports.
- No cycles introduced.
- Existing contracts (A3, A4) should pass without modification.

---

## Cross-cutting concerns

- **C-04 permissions**: first time a non-platform module adds permissions to C-04's tables. Pattern is validated.
- **C-11 audit**: first time a business module emits audit events. Pattern is validated.
- **Receipt number generation**: manual sequential with row locking — acceptable for Phase 1. No C-12 dependency.
- **Academic term**: free-text field — no C-05 dependency. Phase 2 migrates.
- **Ownership check**: app-level, not C-04 owner_id parameter (consistent with D22 deferral).
