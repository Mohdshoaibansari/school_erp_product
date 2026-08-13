# Impact Classification — C-02 UserProfile Self-Service & Admin Management

> **Status:** Impact classification (input to sdd-stack)
> **Capability:** C-02 Identity & User Management (intersecting C-04 Authorization)
> **Decisional inputs:** `docs/prd/c-02-user-profile-ownership.md` (PRD), D13 decisions

---

## Classification

- **Domain status:** EXISTING (C-02, C-04)
- **Delta type:** MODIFIED (UserProfile model, routes, permissions, authorization logic)
- **Cross-cutting:** YES — C-02 (UserProfile model, routes) and C-04 (role-permission mappings, `_check_impl`)

## ADDED requirements

### C-04 — authorization
- **`user_profile.admin` permission** — New permission for Admin/CD/institution_admin. Enables managing any profile via Casbin check. (D13-a)

## MODIFIED requirements

### C-02 — identity-user-management
- **UserProfile FK** — `UserProfile.user_id` FK → `user_account.id` (D12 pattern, D13-c)
- **Profile routes** — Check `user_profile.admin` instead of `user_profile.create/read/update` for non-self access (D13-a)

### C-04 — authorization
- **`_check_impl` Stage 5 removed** — Ownership check (admin bypass) removed. Self-access (Stage 3) + Casbin (Stage 4) handle all cases. (D13-b)

## REMOVED behavior
- **Stage 5 ownership check** — Removed from `_check_impl`. Only profile routes used it. No other resource affected.
- **`user_profile.create/read/update` permissions for admin management** — Replaced by `user_profile.admin`.

## Artifacts affected

| Artifact | Action |
|---|---|
| `docs/prd/c-02-user-profile-ownership.md` | Done (PRD) |
| `docs/prd/c-02-user-profile-impact-classification.md` | This document |
| `openspec/changes/fix-user-profile-ownership/specs/identity-user-management/spec.md` | Update (D13-a: user_profile.admin) |
| `openspec/changes/fix-user-profile-ownership/specs/authorization/spec.md` | Update (D13-b: remove Stage 5, add user_profile.admin) |
| `backend/kernel/authz/dependencies.py` | Remove Stage 5 |
| `backend/kernel/user/routes/profiles.py` | Check `user_profile.admin` |
| `backend/migrations/versions/` | New migration for user_profile.admin permission |
