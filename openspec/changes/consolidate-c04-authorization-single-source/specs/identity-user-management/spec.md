# Delta Spec — C-02 Identity & User Management (MODIFIED)

> **Change:** `consolidate-c04-authorization-single-source`
> **Base:** `openspec/changes/archive/2026-07-11-add-c02-identity-user-management/specs/identity-user-management/spec.md`
> **Impact classification:** MODIFIED
> **ADR decisions:** D7, D19

---

## MODIFIED Behavior — C-02 Routes Pass Object Attributes

All C-02 routes that call `require_permission` SHALL pass `obj_client_id` and `obj_institution_id` for ABAC enforcement (D7, D19). Each route pre-fetches the resource (user, profile, role_assignment, identifier) to obtain its `client_id` and/or `institution_id`, then passes them to `require_permission`.

Trace: D7, D19.

### Affected Route Patterns

| Route pattern | Resource | Action | Object attributes |
|---|---|---|---|
| `POST /api/v1/users` | user | create | `obj_client_id=ctx.client_id, obj_institution_id=ctx.institution_id` (optimistic) |
| `GET /api/v1/users/{id}` | user | read | `obj_client_id=user.client_id, obj_institution_id=user.institution_id` |
| `PUT /api/v1/users/{id}` | user | update | `obj_client_id=user.client_id, obj_institution_id=user.institution_id` |
| `POST /api/v1/users/{id}/suspend` | user | suspend | `obj_client_id=user.client_id, obj_institution_id=user.institution_id` |
| `DELETE /api/v1/users/{id}` | user | delete | `obj_client_id=user.client_id, obj_institution_id=user.institution_id` |
| `GET /api/v1/users` | user | read | `obj_client_id=ctx.client_id` (list endpoint) |
| `GET /api/v1/user-profiles/{id}` | user_profile | read | `obj_client_id=profile.client_id, obj_institution_id=profile.institution_id` |
| `PUT /api/v1/user-profiles/{id}` | user_profile | update | `obj_client_id=profile.client_id, obj_institution_id=profile.institution_id` |
| `POST /api/v1/user-profiles` | user_profile | create | `obj_client_id=ctx.client_id, obj_institution_id=ctx.institution_id` (optimistic) |
| `GET /api/v1/role-assignments` | role_assignment | read | `obj_client_id=ctx.client_id` (list endpoint) |
| `POST /api/v1/role-assignments` | role_assignment | create | `obj_client_id=ctx.client_id, obj_institution_id=ctx.institution_id` (optimistic) |
| `DELETE /api/v1/role-assignments/{id}` | role_assignment | delete | `obj_client_id=ra.client_id, obj_institution_id=ra.institution_id` |
| `GET /api/v1/user-identifiers/{id}` | user_identifier | read | `obj_client_id=ident.client_id, obj_institution_id=ident.institution_id` |
| `POST /api/v1/user-identifiers` | user_identifier | create | `obj_client_id=ctx.client_id, obj_institution_id=ctx.institution_id` (optimistic) |
| `DELETE /api/v1/user-identifiers/{id}` | user_identifier | delete | `obj_client_id=ident.client_id, obj_institution_id=ident.institution_id` |
| `GET /api/v1/lookups/user-categories` | user_category | read | `obj_client_id=ctx.client_id` (lookup, no specific resource) |
| `GET /api/v1/lookups/roles` | role | read | `obj_client_id=ctx.client_id` (lookup, no specific resource) |

#### Scenario: C-02 routes pass resource-derived object attributes
- **WHEN** any C-02 route is invoked
- **THEN** the route pre-fetches the resource (if applicable) and passes `obj_client_id` and `obj_institution_id` to `require_permission`

#### Scenario: Create endpoints pass optimistic attributes
- **WHEN** a create endpoint is called (resource doesn't exist yet)
- **THEN** the route passes `ctx.client_id` and/or `ctx.institution_id` as optimistic object attributes

#### Scenario: List endpoints pass client scope only
- **WHEN** a list endpoint is called (no specific resource ID)
- **THEN** the route passes `ctx.client_id` as `obj_client_id` and omits `obj_institution_id`

#### Scenario: Lookup endpoints pass client scope
- **WHEN** a lookup endpoint (user_category, role list) is called
- **THEN** the route passes `ctx.client_id` as `obj_client_id`

---

## Ownership Enforcement — Unchanged

The ownership enforcement behavior for profile endpoints (`owner_id` parameter) is unchanged. The `require_permission` dependency still enforces ownership checks after Casbin passes. The ABAC object-attribute change does not affect ownership logic.

Trace: D12, D22.

#### Scenario: Profile ownership check still works
- **WHEN** a Teacher (user_id=UUID-A) calls `require_permission("user", "read", owner_id=UUID-B)`
- **THEN** Casbin passes (Teacher has `user.read`), ownership check fails (`owner_id != ctx.user_id`), Teacher does NOT have institution scope → HTTP 403

#### Scenario: Admin still bypasses ownership check
- **WHEN** an Admin calls `require_permission("user", "read", owner_id=UUID-A)`
- **THEN** Casbin passes, ownership check fails, but Admin has institution scope → passes silently

---

## Boundary Relationships (Updated)

| Relationship | Direction | Other capability | Nature |
|---|---|---|---|
| C-02 routes pass object attributes to `require_permission` | C-02 → C-04 | Authorization | Callers update calls; dependency unchanged |
| `platform_owner` role row exists in C-02's `role` table | C-04 → C-02 | Authorization | Unchanged from original C-04 change |
| Ownership enforcement on profile endpoints | C-02 → C-04 | Authorization | Unchanged |
