# Delta Spec — Authorization (Person-Model Revamp)

> **Change:** `add-c02-identity-person-model-revamp`
> **Domain:** authorization
> **Delta type:** MODIFIED (conditional / Q8-dependent)
> **Base spec:** `openspec/specs/authorization/spec.md`
> **Source ADR:** `docs/architecture/adr-c02-identity-person-model-revamp.md` (D3d, D8)
> **Source PRD:** `docs/prd/c02-identity-person-model-revamp.md` (AC-17, AC-18)

---

## MODIFIED Requirements (conditional)

### REQ-AUTHZ-01: Authorization Pipeline Unchanged (Modified — no behavioral change, Q8-conditional referent)

No authz policy, permission, or role definition SHALL change as a result of this revamp (AC-17, AC-18). Roles SHALL remain on `app_user`/`client_user` via `role_assignment`; the Casbin middleware SHALL read roles off the account with NO per-request `person` joins (D3d, D8). `person` is role-agnostic. The only conditional change is the `role_assignment.user_id` referent, which depends on Q8.

#### Scenario: Authz pipeline byte-for-byte unchanged
- **WHEN** the Casbin middleware processes any authenticated request
- **THEN** it SHALL read roles from the account via `role_assignment` (institution) or `client_user.role_id` (client-leadership)
- **AND** SHALL NOT perform per-request `person` joins
- **AND** all existing authz tests SHALL pass without modification

#### Scenario: No policy/permission/role-definition change
- **WHEN** the authorization spec and Casbin policy definitions are inspected
- **THEN** no permission, role definition, or role-permission mapping SHALL change
- **AND** the `platform_owner` bypass SHALL remain (defense-in-depth)

---

## Account-Parent Model (Resolved — D3f: person and user_account coexist)

> **Q8 RESOLVED as D3f:** `person` and `user_account` coexist. `role_assignment.user_id` SHALL target `user_account.id` (unchanged). **No delta is required to this domain** beyond the note above — the Casbin loader query is unchanged, and the authz pipeline is byte-for-byte unchanged. See `identity-user-management` delta spec §Creation Flow for the full resolution.

### REQ-AUTHZ-Q8-01: role_assignment.user_id Referent (Resolved — D3f, no change needed)

`role_assignment.user_id` SHALL target `user_account.id` (UNCHANGED). Roles are account-scoped (D8 + D3b); `person` and `user_account` coexist (D3f). The Casbin loader query text is unchanged. No further delta is needed in this domain.

#### Scenario: role_assignment referent unchanged (confirmed)
- **WHEN** the `role_assignment` FK and Casbin loader are inspected
- **THEN** `role_assignment.user_id` SHALL reference `user_account.id`
- **AND** the Casbin loader query SHALL be unchanged
- **AND** no authz policy, permission, or role-definition change SHALL result from this revamp
