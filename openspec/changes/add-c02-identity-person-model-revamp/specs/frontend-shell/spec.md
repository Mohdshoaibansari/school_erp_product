# Delta Spec — Frontend Shell (Person-Model Revamp)

> **Change:** `add-c02-identity-person-model-revamp`
> **Domain:** frontend-shell
> **Delta type:** MODIFIED (Breaking)
> **Base spec:** `openspec/specs/frontend-shell/spec.md`
> **Source ADR:** `docs/architecture/adr-c02-identity-person-model-revamp.md` (D6a, D3d, D8)
> **Source PRD:** `docs/prd/c02-identity-person-model-revamp.md` (AC-25, AC-26)

---

## MODIFIED Requirements

### REQ-SHELL-09: Typed DTO API Layer (Modified — person projection, breaking)

All API responses SHALL map to typed DTOs in the UI API layer (mirroring backend DTOs). The `UserDTO` type SHALL be updated to include a `person` projection (`PersonDTO`: name, dob, gender, blood_group, photo, contact, demographics) sourced from the `person` entity. The `UserDTO` type SHALL NOT include `user_category_id` or any flat `user_profile` fields. The use of `any` SHALL remain disallowed in the API layer. This is a **breaking contract change** — the frontend's user-display and user-filter paths SHALL be updated to source human data from `user.person.*` and SHALL NOT reference `user.user_category_id` or `user.user_profile.*`. Per AC-25, AC-26.

#### Scenario: UserDTO typed with person projection
- **WHEN** the API layer receives a user response
- **THEN** it SHALL map to a typed `UserDTO` containing a `person: PersonDTO` field
- **AND** the `UserDTO` type SHALL NOT include `user_category_id` or flat `user_profile` fields
- **AND** untyped `any` handling SHALL remain disallowed

#### Scenario: Frontend user-display reads from person projection
- **WHEN** the frontend displays a user's name or profile fields
- **THEN** it SHALL read from `user.person.name` / `user.person.*`
- **AND** SHALL NOT attempt to read `user.user_category_id` or `user.user_profile.*`

#### Scenario: user_category filter removed
- **WHEN** the frontend renders user-list filters
- **THEN** there SHALL be no `user_category` dropdown or filter
- **AND** filtering SHALL be by role/institution (not by category)

---

### REQ-SHELL-10: All 10 Backend Roles (Modified — no role change, DTO only)

The frontend SHALL serve all 10 backend roles derived from the JWT roles array with `user_tier`/`is_platform_owner` fallback. Role definitions and permission-accurate gating are **unchanged** (D3d, D8 — roles stay on accounts; no authz policy/role-definition change). The only change in this domain is the `UserDTO` type update (REQ-SHELL-09). Per AC-17, AC-18.

#### Scenario: Role list unchanged (no regression)
- **WHEN** the frontend renders role-filtered navigation
- **THEN** the 10 roles SHALL be served as before
- **AND** `is_platform_owner` fallback SHALL remain
- **AND** no role definition or permission gating SHALL change

#### Scenario: Platform owner discovery via flag (not category)
- **WHEN** the frontend determines if a user is a Platform Owner
- **THEN** it SHALL use the `is_platform_owner` claim from the JWT
- **AND** SHALL NOT reference any `user_category` value

---

## Notes

- **PRD Q5 (sequencing):** The frontend is already archived. Whether the frontend update lands in this revamp's PR or as a residual follow-up is a product decision. This delta flags the breaking change; the parent session determines sequencing.
- **No authz route consumption:** The frontend does not consume C-04 authorization routes. Role-based gating is derived from the JWT `roles` claim only (R1). This is unchanged by the person-model revamp.
