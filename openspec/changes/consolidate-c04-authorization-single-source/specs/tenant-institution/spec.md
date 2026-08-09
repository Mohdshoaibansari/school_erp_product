# Delta Spec — C-01 Tenant & Institution (MODIFIED)

> **Change:** `consolidate-c04-authorization-single-source`
> **Base:** `openspec/changes/archive/2026-07-08-add-c01-tenant-institution/specs/tenant-institution/spec.md`
> **Impact classification:** MODIFIED
> **ADR decisions:** D11, D14

---

## MODIFIED Requirements

### Requirement: C-01 Write-Permission Matrix — Source Migration

The tiered delegation write-permission matrix (D11) SHALL be sourced entirely from C-04's `role_permission` table, NOT from C-01's hardcoded `policies.py`. The behavioral contract (who can do what) is unchanged — only the source of truth moves from Python code to the database.

**Supersedes** the archived spec's "C-01 Write-Permission Matrix" requirement — the permission matrix content is unchanged, but the enforcement source moves from C-01 hardcoded policies to C-04 DB-driven policies.

Trace: D11, D14, AC-15.

#### Scenario: All D11 permissions enforced via C-04 DB
- **WHEN** any C-01 mutation is authorized
- **THEN** the authorization decision comes from the Casbin enforcer loaded with policies from C-04's `role_permission` table, NOT from C-01's `policies.py`

#### Scenario: Behavioral contract unchanged
- **WHEN** the D11 matrix is tested after consolidation
- **THEN** every role×resource×action combination produces the same allow/deny result as before (the permission matrix content is preserved)

---

## REMOVED Requirements

### Requirement: C-01 Policies File (REMOVED)

The file `business/tenant_institution/policies.py` SHALL be deleted (D14). This file contained the hardcoded `PERMISSION_POLICIES` dictionary and the `ROLE_HIERARCHY` mapping. All policies are migrated to C-04's `role_permission` table.

Trace: D14, AC-1, AC-3.

#### Scenario: policies.py no longer exists
- **WHEN** the codebase is searched for `business/tenant_institution/policies.py`
- **THEN** the file does not exist

#### Scenario: No imports of policies.py remain
- **WHEN** the codebase is searched for imports from `policies` or `PERMISSION_POLICIES` or `ROLE_HIERARCHY`
- **THEN** no references remain in any source file

---

### Requirement: C-01 Duplicate Casbin Model (REMOVED)

The file `business/tenant_institution/casbin_model.conf` SHALL be deleted (D14). The only Casbin model file SHALL be at `kernel/authz/casbin_model.conf`.

Trace: D14, AC-2.

#### Scenario: Duplicate model file no longer exists
- **WHEN** the codebase is searched for `business/tenant_institution/casbin_model.conf`
- **THEN** the file does not exist

#### Scenario: Central model file still exists
- **WHEN** the codebase is searched for `kernel/authz/casbin_model.conf`
- **THEN** the file exists and contains the Casbin model

---

### Requirement: C-01 `register_casbin_policies` Hook (REMOVED)

C-01's manifest SHALL NOT register any Casbin policies (D14). The `register_casbin_policies` hook in C-01's manifest SHALL be removed or made a no-op. C-04 is the sole owner of policy registration.

**Supersedes** the archived spec's requirement that C-01's `register_casbin_policies(enforcer)` hook "continue to add D11 policies." That requirement is now REMOVED — C-01 no longer registers any policies.

Trace: D14, AC-4.

#### Scenario: C-01 manifest does not register policies
- **WHEN** the app starts and the factory iterates module manifests
- **THEN** C-01's manifest either has no `register_casbin_policies` hook or the hook is a no-op (empty body)

#### Scenario: C-04 is sole policy owner
- **WHEN** the app starts
- **THEN** only C-04's manifest registers Casbin policies (from `role_permission` DB table)

---

### Requirement: C-01 `build_enforcer` Function (REMOVED)

The `build_enforcer()` function in C-01's `policies.py` SHALL be removed (D14). The central Casbin enforcer is created by C-04's `kernel/authz/` package.

Trace: D14.

#### Scenario: build_enforcer no longer exists
- **WHEN** the codebase is searched for `build_enforcer`
- **THEN** the function does not exist in C-01's code

---

## MODIFIED Behavior — C-01 Routes Pass Object Attributes

All C-01 routes that call `require_permission` SHALL pass `obj_client_id` and `obj_institution_id` for ABAC enforcement (D7, D19). Each route pre-fetches the resource to obtain its `client_id` and `institution_id`, then passes them to `require_permission`.

Trace: D7, D19.

### Affected Route Patterns

| Route pattern | Resource | Action | Object attributes |
|---|---|---|---|
| `POST /api/v1/institutions` | institution | create | `obj_client_id=ctx.client_id` (optimistic, resource doesn't exist yet) |
| `GET /api/v1/institutions/{id}` | institution | read | `obj_client_id=inst.client_id, obj_institution_id=inst.id` |
| `PUT /api/v1/institutions/{id}` | institution | update | `obj_client_id=inst.client_id, obj_institution_id=inst.id` |
| `POST /api/v1/institutions/{id}/transition` | institution | transition_lifecycle | `obj_client_id=inst.client_id, obj_institution_id=inst.id` |
| `GET /api/v1/institutions` | institution | list | `obj_client_id=ctx.client_id` (list endpoint, no specific ID) |
| `POST /api/v1/institutions/{id}/archive` | institution | archive | `obj_client_id=inst.client_id, obj_institution_id=inst.id` |
| `GET /api/v1/clients/{id}` | client | read | `obj_client_id=client.id` |
| `PUT /api/v1/clients/{id}` | client | update | `obj_client_id=client.id` |
| `POST /api/v1/org-units` | org_unit | create | `obj_client_id=ctx.client_id, obj_institution_id=ctx.institution_id` |
| `GET /api/v1/org-units/{id}` | org_unit | read | `obj_client_id=ou.client_id, obj_institution_id=ou.institution_id` |
| `PUT /api/v1/org-units/{id}` | org_unit | update | `obj_client_id=ou.client_id, obj_institution_id=ou.institution_id` |
| `DELETE /api/v1/org-units/{id}` | org_unit | delete | `obj_client_id=ou.client_id, obj_institution_id=ou.institution_id` |
| `POST /api/v1/org-units/{id}/move` | org_unit | move | `obj_client_id=ou.client_id, obj_institution_id=ou.institution_id` |
| `POST /api/v1/org-units/{id}/archive` | org_unit | archive | `obj_client_id=ou.client_id, obj_institution_id=ou.institution_id` |
| `POST /api/v1/org-units/{id}/reactivate` | org_unit | reactivate | `obj_client_id=ou.client_id, obj_institution_id=ou.institution_id` |
| `POST /api/v1/org-units/reorder` | org_unit | reorder | `obj_client_id=ctx.client_id, obj_institution_id=ctx.institution_id` |

#### Scenario: C-01 routes pass resource-derived object attributes
- **WHEN** any C-01 route is invoked
- **THEN** the route pre-fetches the resource (if applicable) and passes `obj_client_id` and `obj_institution_id` to `require_permission`

#### Scenario: Create endpoints pass optimistic attributes
- **WHEN** a create endpoint is called (resource doesn't exist yet)
- **THEN** the route passes `ctx.client_id` and/or `ctx.institution_id` as optimistic object attributes

#### Scenario: List endpoints pass client scope only
- **WHEN** a list endpoint is called (no specific resource ID)
- **THEN** the route passes `ctx.client_id` as `obj_client_id` and omits `obj_institution_id`

---

## Boundary Relationships (Updated)

| Relationship | Direction | Other capability | Nature |
|---|---|---|---|
| C-01 no longer registers Casbin policies | C-01 → C-04 | Authorization | C-04 is sole policy owner |
| C-01 routes pass object attributes to `require_permission` | C-01 → C-04 | Authorization | Callers update calls; dependency unchanged |
| RLS backstop unchanged | C-01 → C-01 | Self | RLS policies remain as defense-in-depth |
| C-01 still emits C-11 audit events | C-01 → C-11 | Audit | Unchanged |
