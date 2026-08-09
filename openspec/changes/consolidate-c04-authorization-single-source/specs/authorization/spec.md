# Delta Spec — C-04 Authorization (MODIFIED)

> **Change:** `consolidate-c04-authorization-single-source`
> **Base:** `openspec/changes/archive/2026-07-14-add-c04-authorization/specs/authorization/spec.md`
> **Impact classification:** MODIFIED
> **ADR decisions:** D7, D11, D14, D18, D19, D26, D27, D28

---

## MODIFIED Requirements

### Requirement: Permission Catalog — Add Missing Permissions

The `permission` table SHALL contain 35 rows (26 existing + 9 new) covering C-01, C-02, and the previously missing permissions (D18). The 9 new permissions are: `institution.archive`, `institution.list`, `org_unit.archive`, `org_unit.reactivate`, `org_unit.reorder`, `institution_type.create`, `institution_type.update`, `user_profile.create`, `user.delete`.

**Supersedes** the archived spec's "Permission Catalog" requirement — the row count changes from 26 to 35 and the C-01/C-02 coverage boundary changes.

Trace: D18, D30.

#### Scenario: 35 permissions are seeded after migration
- **WHEN** Alembic migration 016 is applied
- **THEN** the `permission` table contains exactly 35 rows including the 9 new permissions listed above

#### Scenario: New permissions are idempotent
- **WHEN** migration 016 is re-applied (ON CONFLICT DO NOTHING)
- **THEN** no duplicate rows are created and the table still contains exactly 35 rows

---

### Requirement: Role-Permission Mapping — Add Scope Column

The `role_permission` table SHALL have a `scope` column (`VARCHAR(20) NOT NULL DEFAULT 'institution'`) mapping directly to Casbin policy scope (D26). Valid values: `any` (no tenant check), `tenant` (own-client), `institution` (own-institution).

**Supersedes** the archived spec's "Role-Permission Mapping" requirement — adds the scope dimension.

Trace: D26, AC-6.

#### Scenario: Scope column exists on role_permission
- **WHEN** migration 016 is applied
- **THEN** the `role_permission` table has a `scope` column with type `VARCHAR(20)`, `NOT NULL`, default `'institution'`

#### Scenario: Existing C-02 role_permissions backfilled to institution scope
- **WHEN** migration 016 is applied
- **THEN** all existing rows (from migration 004) have `scope = 'institution'`

#### Scenario: Scope column maps to Casbin policy
- **WHEN** C-04's policy loader reads `role_permission` rows at startup
- **THEN** each row's `scope` value is passed as the fourth element of the Casbin policy tuple `(role, resource, action, scope)`

---

### Requirement: C-01 Role Migration to role_permission

The roles `client_director`, `institution_admin`, and `cross_institution` SHALL have their permission mappings in the `role_permission` table (D11). This replaces C-01's hardcoded `PERMISSION_POLICIES` dictionary.

**client_director** (scope: `tenant`): `institution.create`, `institution.read`, `institution.update`, `institution.transition_lifecycle`, `institution.archive`, `institution.list`, `client.read`, `client.update`, `org_unit.create`, `org_unit.read`, `org_unit.update`, `org_unit.move`, `org_unit.archive`, `org_unit.reactivate`, `org_unit.reorder`.

**institution_admin** (scope: `institution`): `institution.read`, `institution.update`, `org_unit.create`, `org_unit.read`, `org_unit.update`, `org_unit.move`, `org_unit.archive`, `org_unit.reactivate`, `org_unit.reorder`.

**cross_institution** (scope: `tenant`): `client.read`, `institution.read`, `org_unit.read`.

Trace: D11, AC-3, AC-8, AC-9, AC-10.

#### Scenario: client_director has all D11 permissions with tenant scope
- **WHEN** querying `role_permission` joined with `role` and `permission` for the `client_director` role
- **THEN** the result set contains 15 permission rows (listed above), all with `scope = 'tenant'`

#### Scenario: institution_admin has own-institution permissions with institution scope
- **WHEN** querying `role_permission` joined with `role` and `permission` for the `institution_admin` role
- **THEN** the result set contains 9 permission rows (listed above), all with `scope = 'institution'`

#### Scenario: cross_institution has read-only permissions with tenant scope
- **WHEN** querying `role_permission` joined with `role` and `permission` for the `cross_institution` role
- **THEN** the result set contains 3 permission rows (`client.read`, `institution.read`, `org_unit.read`), all with `scope = 'tenant'`

#### Scenario: CD transition_lifecycle action name matches route
- **WHEN** a `client_director` calls `require_permission("institution", "transition_lifecycle", ...)`
- **THEN** the Casbin enforcer finds a matching policy `(client_director, institution, transition_lifecycle, tenant)` — the action name mismatch bug is fixed

---

### Requirement: `require_permission` — Accept Object Attributes

The `require_permission` dependency SHALL accept `obj_client_id: uuid.UUID | None = None` and `obj_institution_id: uuid.UUID | None = None` keyword parameters (D7, D19). When provided, the Casbin object SHALL be built from these parameters instead of from `ctx`. When not provided, backward-compatible behavior: object attributes default from `ctx` (existing callers continue to work).

**Supersedes** the archived spec's "`require_permission` FastAPI Dependency" requirement — the signature changes and ABAC enforcement becomes real.

Trace: D7, D19, AC-11, AC-12, AC-13, AC-14, AC-15.

#### Scenario: Object attributes from parameters override ctx
- **WHEN** `require_permission("institution", "read", obj_client_id=B, obj_institution_id=B1)` is called with `ctx.client_id=A`
- **THEN** the Casbin object is `{"name": "institution", "client_id": B, "institution_id": B1}` — NOT from ctx

#### Scenario: Cross-tenant block enforced at Casbin layer
- **WHEN** a CD (client_id=A) calls `require_permission("institution", "read", obj_client_id=B)`
- **THEN** Casbin checks `sub.client_id (A) == obj.client_id (B)` → fails → HTTP 403

#### Scenario: Same-tenant access passes
- **WHEN** a CD (client_id=A) calls `require_permission("institution", "read", obj_client_id=A)`
- **THEN** Casbin checks `sub.client_id (A) == obj.client_id (A)` → passes

#### Scenario: Cross-institution block enforced at Casbin layer
- **WHEN** an Admin (institution_id=X) calls `require_permission("user", "create", obj_institution_id=Y)`
- **THEN** Casbin checks `sub.institution_id (X) == obj.institution_id (Y)` → fails → HTTP 403

#### Scenario: Backward compatibility — no object attributes
- **WHEN** an existing caller uses `require_permission("user", "read")` without object attributes
- **THEN** the dependency falls back to ctx values (existing behavior preserved)

---

### Requirement: Policy Loader — Read Scope from DB

C-04's policy loader SHALL read the `scope` column from `role_permission` when building Casbin policies at startup (D26). Each policy tuple SHALL be `(role_name, resource, action, scope)`.

**Supersedes** the archived spec's "C-04 Policy Registration" requirement — the policy tuple gains the scope element from DB.

Trace: D26, D24, AC-12, AC-13.

#### Scenario: Policy tuple includes scope from DB
- **WHEN** the app starts and the policy loader reads `role_permission` rows
- **THEN** each Casbin policy added to the enforcer is `(role_name, resource, action, scope)` where scope comes from the `role_permission.scope` column

#### Scenario: Scope values map to Casbin scope semantics
- **WHEN** a policy with `scope = 'tenant'` is evaluated
- **THEN** Casbin checks `sub.client_id == obj.client_id`
- **WHEN** a policy with `scope = 'institution'` is evaluated
- **THEN** Casbin checks `sub.institution_id == obj.institution_id`
- **WHEN** a policy with `scope = 'any'` is evaluated
- **THEN** no tenant/institution check is performed

---

### Requirement: Platform Owner Bypass — Retained

The `require_permission` dependency SHALL retain its early-return for `ctx.is_platform_owner` (D27, D28). The `role_permission` table SHALL NOT contain any mapping for `platform_owner` (D27). Platform Owner bypass is code-only.

**No change** from archived spec — this requirement is preserved as-is.

Trace: D27, D28, AC-16, AC-17, AC-18.

#### Scenario: Platform Owner bypasses all checks
- **WHEN** a Platform Owner calls `require_permission` for any resource, action, and object attributes
- **THEN** the dependency returns silently (no 403) before Casbin enforcement runs

#### Scenario: platform_owner has no role_permission entries
- **WHEN** querying `role_permission` for the `platform_owner` role
- **THEN** the result set is empty

---

## REMOVED Requirements

### C-01 Casbin Model Relocation (removed — superseded by tenant-institution REMOVED)

The archived spec's "C-01 Casbin Model Relocation" requirement assumed C-01's `register_casbin_policies` hook would continue to exist. This consolidation REMOVES that hook entirely (see `tenant-institution` delta spec). The Casbin model relocation happened in the original C-04 change; this consolidation completes the cleanup by removing the duplicate model file and the C-01 policy registration hook.

---

## Boundary Relationships

| Relationship | Direction | Other capability | Nature |
|---|---|---|---|
| `require_permission` signature change | C-04 → all modules | C-01, C-02, fees, homework | Callers update their calls; dependency unchanged |
| Platform owner bypass retained | C-04 → C-01 | C-01 platform routes | No behavior change |
| RLS backstop | C-04 → C-04 | Self | RLS policies unchanged |
| Permission table is global (no RLS) | C-04 → C-08 | Config | Permission table is read at startup, not config-driven |
