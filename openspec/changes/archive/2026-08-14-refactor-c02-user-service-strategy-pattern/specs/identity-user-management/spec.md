# identity-user-management — Delta Spec (C-02 User Service Strategy Pattern Refactor)

> **Change:** `refactor-c02-user-service-strategy-pattern`
> **Domain:** C-02 Identity & User Management
> **Delta type:** MODIFIED (service architecture refactor — `IdentityUserService` and `ClientUserService` replaced by a single `UserService` with `StrategyResolver`)
> **Source:** `docs/architecture/adr-c02-identity-user-management-implementation.md` D6-D10; `docs/architecture/audit-c02-implementation-2026-08-03.md`
> **Predecessor:** `openspec/changes/add-c02-user-creation-activation/specs/identity-user-management/spec.md` (D1-D5 unified activation, role-at-creation, config-driven invite URL)

This delta is a MODIFIED evolution of the predecessor spec. Requirements from the predecessor that are unchanged are NOT repeated here; this delta explicitly states what changed.

---

## MODIFIED Requirements

### Requirement: Single `UserService` replaces `IdentityUserService` and `ClientUserService`

The user-management domain has a single service class: `UserService` (`backend/kernel/user/services/service.py`). It replaces the two parallel services (`IdentityUserService` for `app_user`, `ClientUserService` for `client_user`) that the predecessor spec created.

`UserService` exposes the full symmetric strategy interface: `create_user`, `update_user`, `delete_user`, `get_user`, `list_users`, `transition_lifecycle`. Both strategies (`CDStrategy` and `InstitutionUserStrategy`) implement every method.

`AuthService` (`backend/kernel/auth/services/service.py`) remains a separate service for login, refresh, logout, activate, OTP, and password-reset flows. The user-lifecycle and authentication concerns are split between the two services (per D6).

#### Scenario: `UserService` is the only user-lifecycle service in the DI graph
- WHEN `kernel/user/dependencies.py:get_identity_user_service` is resolved
- THEN it SHALL return a `UserService` instance (not `IdentityUserService` or `ClientUserService`)

#### Scenario: `ClientUserService` is deleted
- WHEN the refactor completes
- THEN `backend/kernel/user/services/client_user_service.py` SHALL not exist

### Requirement: `StrategyResolver` dispatches by DTO type for create, by DB lookup for others

`UserService` has an internal `StrategyResolver` that picks the right strategy based on the operation:

- **For `create_user(ctx, dto)`:** the resolver dispatches on DTO type. `isinstance(dto, ClientUserCreateDTO)` → `CDStrategy`. `isinstance(dto, UserCreateDTO)` → `InstitutionUserStrategy`. The DTO class type IS the tier discriminator.
- **For `update_user`, `delete_user`, `get_user`, `list_users`, `transition_lifecycle`:** the resolver first reads the user record (by ID or query filter) to determine the tier, then dispatches to the corresponding strategy. The tier is sourced from the database, not from the caller.

`ClientUserService` is removed; its logic is split between `CDStrategy` (PO bootstrap, CD row CRUD) and `UserService` (CD lifecycle transitions, role assignment).

#### Scenario: create_user dispatches by DTO type
- WHEN `await user_service.create_user(ctx, ClientUserCreateDTO(email=..., name=..., role_id=..., user_category_id=..., client_id=...))` is called
- THEN the resolver SHALL dispatch to `CDStrategy.create_user(ctx, dto)`
- AND the result SHALL be `{"user": ClientUserDTO, "invite_url": "..."}`

#### Scenario: create_user dispatches institution DTO to institution strategy
- WHEN `await user_service.create_user(ctx, UserCreateDTO(email=..., name=..., user_category_id=..., institution_id=..., role_id=...))` is called
- THEN the resolver SHALL dispatch to `InstitutionUserStrategy.create_user(ctx, dto)`
- AND the result SHALL be `{"user": UserDTO, "invite_url": "..."}`

#### Scenario: update_user dispatches by DB lookup
- WHEN `await user_service.update_user(ctx, user_id, UserUpdateDTO(name=...))` is called
- AND the user record at `user_id` has `tier="client_leadership"` (CD)
- THEN the resolver SHALL look up the user record, read the tier, and dispatch to `CDStrategy.update_user(ctx, user_id, dto)`
- AND the result SHALL be `ClientUserDTO` (not `UserDTO`)

#### Scenario: update_user dispatches institution by DB lookup
- WHEN `await user_service.update_user(ctx, user_id, UserUpdateDTO(name=...))` is called
- AND the user record at `user_id` has `tier="institution"`
- THEN the resolver SHALL look up the user record, read the tier, and dispatch to `InstitutionUserStrategy.update_user(ctx, user_id, dto)`
- AND the result SHALL be `UserDTO`

#### Scenario: get_user returns the right DTO type
- WHEN `user_service.get_user(ctx, user_id)` is called
- AND the user is a CD
- THEN the result SHALL be `ClientUserDTO` with `client_id` populated
- WHEN the user is institution-tier
- THEN the result SHALL be `UserDTO` with `institution_id` populated

### Requirement: Both strategies emit audit events symmetrically

Every `create_user`, `update_user`, `delete_user`, `transition_lifecycle` call emits an audit event. The payload includes the user_id, email, name, and either `client_id` (CD) or `institution_id` (institution).

`CDStrategy.create_user` emits `action="user_created"` with payload `{user_id, email, name, client_id}`. This fixes the audit-emission gap that the 2026-08-03 audit found in the predecessor (`ClientUserService.bootstrap_invite` did not emit).

#### Scenario: CD create_user emits audit
- WHEN `user_service.create_user(ctx, ClientUserCreateDTO(...))` is called
- AND the operation succeeds
- THEN `CDStrategy.create_user` SHALL emit an audit event `action="user_created"` with payload `{user_id, email, name, client_id}`

#### Scenario: institution create_user emits audit
- WHEN `user_service.create_user(ctx, UserCreateDTO(...))` is called
- AND the operation succeeds
- THEN `InstitutionUserStrategy.create_user` SHALL emit an audit event `action="user_created"` with payload `{user_id, email, name, institution_id}`

### Requirement: Both strategies do cross-tenant checks

`CDStrategy.login` checks `ctx.client_id == user_obj.client_id`. This fixes the security gap the 2026-08-03 audit found (`_login_client_leadership` did not perform the cross-tenant check, allowing a CD from client A to log in from client B's subdomain).

Note: the cross-tenant check for institution users was already present in the predecessor. This requirement makes the symmetry explicit.

#### Scenario: CD login from wrong subdomain is rejected
- WHEN a CD with `client_id=X` attempts to log in
- AND the request is on subdomain `Y` (which resolves to `client_id=Y` in the `TenantContext`)
- AND `X != Y`
- AND the user is not a Platform Owner
- THEN `CDStrategy.login` SHALL raise `AuthError("Access denied. Account does not belong to this client.", 403)`

#### Scenario: CD login from correct subdomain succeeds
- WHEN a CD with `client_id=X` attempts to log in
- AND the request is on subdomain `X` (which resolves to `client_id=X`)
- THEN `CDStrategy.login` SHALL mint the custom HS256 JWT and return the unified `LoginResponse`

### Requirement: `create_user` validates role before Supabase call is no longer needed at bootstrap (D11)

With D11, bootstrap no longer creates Supabase Auth users. The role validation (existence check on `role` table) still happens before the DB insert, but there is no Supabase call to reorder against. The Supabase Auth user is created during activate, with the password, in a single `POST /admin/users` call.

#### Scenario: invalid role_id fails at bootstrap
- WHEN `InstitutionUserStrategy.create_user` is called with `role_id=<nonexistent uuid>`
- AND the role does not exist in the `role` table
- THEN the strategy SHALL raise `ValueError("Role not found: <uuid>")`
- AND no DB row SHALL be created
- AND no Supabase Auth user SHALL be created (there is no Supabase call at bootstrap)

#### Scenario: valid role_id proceeds normally
- WHEN `InstitutionUserStrategy.create_user` is called with a valid `role_id`
- THEN the strategy SHALL validate the role exists, insert the `app_user` row, insert the `role_assignment` row, and mint the invite JWT
- AND SHALL NOT call `self._supabase.create_user()` (D11)
- AND the response SHALL be `{"user": UserDTO, "invite_url": str}`

### Requirement: Bootstrap does NOT create Supabase Auth users (D11)

Neither `CDStrategy.create_user` nor `InstitutionUserStrategy.create_user` SHALL call `self._supabase.create_user()` during bootstrap. The bootstrap endpoints create only the DB row and mint the invite JWT. The Supabase Auth user is created during activate, with the password, in a single `POST /admin/users` call.

#### Scenario: CD bootstrap does not call Supabase
- WHEN `CDStrategy.create_user(ctx, ClientUserCreateDTO(...))` is called
- THEN the strategy SHALL insert the `user_account` row, then the `client_user` row, assign the role in `role_assignment`, record the lifecycle event, mint the invite JWT, build the invite URL, and emit audit
- AND SHALL NOT call `self._supabase.create_user()`
- AND the Supabase Auth user SHALL NOT exist after bootstrap

#### Scenario: Institution bootstrap does not call Supabase
- WHEN `InstitutionUserStrategy.create_user(ctx, UserCreateDTO(...))` is called
- THEN the strategy SHALL insert the `user_account` row, then the `app_user` row, assign the role if provided, mint the invite JWT, and emit audit
- AND SHALL NOT call `self._supabase.create_user()`
- AND the Supabase Auth user SHALL NOT exist after bootstrap

### Requirement: `user_account` parent table for cross-tier referential integrity (D12)

A `user_account` table serves as the shared identity parent for both `app_user` (institution users) and `client_user` (CD users). Both child tables reference `user_account.id` via FK. The `role_assignment.user_id` and `login_attempt.user_id` FKs point to `user_account.id` instead of `app_user.id`.

When creating any user (CD or institution), the strategy inserts a `user_account` row first, then inserts the child row (`app_user` or `client_user`) with the same UUID. The UUID is generated once and shared across all three tables.

#### Scenario: CD creation inserts user_account first
- WHEN `CDStrategy.create_user(ctx, ClientUserCreateDTO(...))` is called
- THEN the strategy SHALL insert a `user_account` row with a new UUID
- AND then insert a `client_user` row with the same UUID (FK: `id` → `user_account.id`)
- AND then insert a `role_assignment` row with `user_id` = that UUID (FK: `user_id` → `user_account.id` ✅)

#### Scenario: Institution creation inserts user_account first
- WHEN `InstitutionUserStrategy.create_user(ctx, UserCreateDTO(...))` is called
- THEN the strategy SHALL insert a `user_account` row with a new UUID
- AND then insert an `app_user` row with the same UUID (FK: `id` → `user_account.id`)
- AND then insert a `role_assignment` row with `user_id` = that UUID (FK: `user_id` → `user_account.id` ✅)

#### Scenario: role_assignment FK accepts both user types
- WHEN a `role_assignment` row is inserted with `user_id` pointing to a CD user's UUID
- THEN the FK constraint `role_assignment_user_id_fkey` SHALL accept the row (FK target: `user_account.id`)
- AND the row SHALL be queryable for middleware role resolution

#### Scenario: login_attempt FK accepts both user types
- WHEN a `login_attempt` row is inserted with `user_id` pointing to a CD user's UUID
- THEN the FK constraint `login_attempt_user_id_fkey` SHALL accept the row (FK target: `user_account.id`)
- AND the CD login audit trail SHALL be preserved

### Requirement: Long-term evolution: `StrategyResolver` switches to `Organization.type` via `Membership`

This requirement is forward-looking. The current DTO-type dispatch is the initial behavior. The target architecture dispatches based on `Organization.type` queried via the user's `Membership`. When `Organization` and `Membership` entities are introduced (likely in C-01 or a future capability), the resolver will be updated.

This requirement does NOT mandate the introduction of `Organization` or `Membership` in this change. It only states the long-term target.

#### Scenario: future resolver queries Membership
- WHEN `Organization` and `Membership` entities exist
- AND `UserService.create_user` is called
- THEN the resolver SHALL look up the user's `Membership` to determine the tier
- AND the resolver SHALL NOT depend on the DTO class type for dispatch

## REMOVED Requirements

- **`ClientUserService` exists as the PO-only client-user service** — REMOVED. The class is deleted; its logic is in `CDStrategy` and `UserService`.
- **`ClientUserService.bootstrap_invite` returns `{user_id, email, invite_url, client_id}`** — REMOVED. The unified `create_user` returns `{user, invite_url}` for both tiers.
- **CD login mints a custom HS256 JWT without cross-tenant check** — REMOVED. The unified `LoginResponse` carries the same fields, and the cross-tenant check is now performed.

## Cross-references

- Predecessor spec: `openspec/changes/add-c02-user-creation-activation/specs/identity-user-management/spec.md`
- ADR: `docs/architecture/adr-c02-identity-user-management-implementation.md` (D6, D7, D8, D10)
- Audit: `docs/architecture/audit-c02-implementation-2026-08-03.md`
