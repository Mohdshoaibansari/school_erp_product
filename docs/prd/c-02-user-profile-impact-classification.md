# Impact Classification — C-02 UserProfile Self-Service & Ownership

> **Status:** Impact classification (input to sdd-stack)
> **Capability:** C-02 Identity & User Management (intersecting C-04 Authorization)
> **Decisional inputs:** `docs/prd/c-02-user-profile-ownership.md` (PRD), D13 decisions

---

## Classification

- **Domain status:** EXISTING (C-02, C-04) — modifications to existing capability
- **Delta type:** MODIFIED (UserProfile model, routes, permissions)
- **Cross-cutting:** YES — affects C-02 (UserProfile model, routes) and C-04 (role-permission mappings)
- **Recommended OpenSpec change name:** `fix-user-profile-ownership`

## Reasoning

This change fixes 5 issues with the UserProfile system discovered during Flow 16 testing. It touches:

- **C-02 Identity & User Management** — MODIFIED. `UserProfile.user_id` FK changes from `app_user.id` to `user_account.id`. Profile routes add ownership checks. Self-creation logic added.
- **C-04 Authorization** — MODIFIED. `user_profile.create` added for Admin/CD/institution_admin. `user_profile.update` and `user_profile.read` added for all roles.

## ADDED requirements (high-level)

### C-02 — identity-user-management

- **Self-service profile management** — Any authenticated user can create/read/update their own profile without `user_profile.create` permission. Owner_id check on all endpoints. (D13-a, D13-b)
- **Admin profile management** — Admin/CD/institution_admin can create/read/update profiles on behalf of users using `user_profile.create` permission with institution scope bypass. (D13)
- **UserProfile FK fix** — `UserProfile.user_id` FK references `user_account.id` instead of `app_user.id`. Enables CD users to have profiles. (D12 pattern, D13-c)

### C-04 — authorization

- **`user_profile.create` for admin roles** — Added for Admin, client_director, institution_admin with institution scope. (D13)
- **`user_profile.update` for all roles** — Added for Teacher, Staff, Student, Parent with institution scope. (D13)
- **`user_profile.read` for all roles** — Added for Teacher, Staff, Student, Parent with institution scope. (D13)

## MODIFIED behavior

- **`POST /api/v1/users/{id}/profile`** — Allows self-creation (owner_id check) without `user_profile.create`. Admin uses `user_profile.create` for on-behalf creation.
- **`PATCH /api/v1/users/{id}/profile`** — Passes `owner_id=user_id`. Self-only for non-admin. Admin bypass via institution scope.
- **`GET /api/v1/users/{id}/profile`** — Passes `owner_id=user_id`. Self-only for non-admin. Admin bypass via institution scope.

## REMOVED behavior

- **UserProfile FK to `app_user.id`** — Replaced by FK to `user_account.id`.
- **No ownership check on profile endpoints** — Replaced by owner_id enforcement.

## Artifacts affected

| Artifact | Action |
|---|---|
| `docs/prd/c-02-user-profile-ownership.md` | Done (PRD) |
| `docs/prd/c-02-user-profile-impact-classification.md` | This document |
| `openspec/changes/fix-user-profile-ownership/specs/identity-user-management/spec.md` | To create (sdd-stack) |
| `openspec/changes/fix-user-profile-ownership/specs/authorization/spec.md` | To create (sdd-stack) |
| `backend/kernel/user/models/user_profile.py` | FK change |
| `backend/kernel/user/routes/profiles.py` | Ownership checks |
| `backend/migrations/versions/018_user_profile_user_account_fk.py` | New migration |
| `backend/tests/test_c04_authz.py` | Update tests |
