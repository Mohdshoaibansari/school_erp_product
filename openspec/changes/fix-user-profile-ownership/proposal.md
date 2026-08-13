# Proposal — fix-user-profile-ownership

> **Change ID:** fix-user-profile-ownership
> **Capability:** C-02 Identity & User Management (intersecting C-04 Authorization)
> **Delta type:** MODIFIED
> **Status:** Proposal
> **Created:** 2026-08-12
> **Last updated:** 2026-08-13

---

## 1. Problem Summary

Flow 16 testing revealed 5 issues with the UserProfile system:

1. `UserProfile.user_id` FK → `app_user.id` prevents CD users (in `client_user`) from having profiles
2. No role has `user_profile.create` permission — `POST /api/v1/users/{id}/profile` returns 403 for everyone
3. No clean admin vs self-service separation — need a way for admins to manage any profile while restricting non-admins to their own
4. Teacher/Staff/Student/Parent can't manage own profile — missing permissions
5. Stage 5 ownership check in `_check_impl` is broken — uses empty `client_id`/`institution_id`, can't distinguish admin from non-admin roles

---

## 2. Proposed Changes

### 2.1 Identity & User Management (C-02) — MODIFIED

| Change | Description | Key Decision |
|--------|-------------|--------------|
| UserProfile FK fix | `UserProfile.user_id` FK references `user_account.id` instead of `app_user.id` | D13-c |
| Self-service bypass | All authenticated users can manage their own profile via Stage 3 (`owner_id == ctx.user_id`) bypass — no Casbin check needed | D13-a |
| Admin management | Admin/CD/institution_admin can manage any profile via new `user_profile.admin` permission checked at Stage 4 (Casbin) | D13-a |
| Remove Stage 5 | Remove ownership check (Stage 5) from `_check_impl` — self-service (Stage 3) + admin (Stage 4) handle all cases | D13-b |

### 2.2 Authorization (C-04) — MODIFIED

| Change | Description | Key Decision |
|--------|-------------|--------------|
| New `user_profile.admin` permission | Single admin permission replaces `user_profile.create/read/update` for non-self access | D13-a |
| Role-permission mapping | `user_profile.admin` assigned to Admin, client_director, institution_admin only | D13-a |
| Remove `user_profile.create/read/update` from routes | Profile routes check `user_profile.admin` for non-self access instead of per-action permissions | D13-a |
| Remove Stage 5 from `_check_impl` | Ownership check stage is deleted from authorization dependency | D13-b |

---

## 3. Scope Boundaries

### In Scope
- UserProfile FK migration from `app_user.id` to `user_account.id`
- New `user_profile.admin` permission and role mappings
- Stage 3 self-service bypass (`owner_id == ctx.user_id`)
- Removal of Stage 5 (ownership check) from `_check_impl`
- Profile routes use `user_profile.admin` for non-self access
- Migration to backfill existing profile user_ids to `user_account` (same pattern as D12)

### Out of Scope
- Profile photo upload (C-02 Phase 2)
- Profile deletion endpoint
- Bulk profile import

---

## 4. Acceptance Criteria

| ID | Criterion |
|----|-----------|
| AC-1 | `UserProfile.user_id` FK references `user_account.id` |
| AC-2 | `user_profile.admin` permission exists and is assigned to Admin/CD/institution_admin |
| AC-3 | All roles can manage own profile (Stage 3 self-access bypass) |
| AC-4 | Admin/CD/institution_admin can manage any profile (Casbin `user_profile.admin` check) |
| AC-5 | Teacher CANNOT manage another teacher's profile (no `user_profile.admin`) |
| AC-6 | Stage 5 (ownership check) removed from `_check_impl` |
| AC-7 | CD user (in `client_user`) can have a UserProfile (FK fix) |

---

## 5. Traceability

| PRD Section | Key Decision | Spec Domain |
|-------------|--------------|-------------|
| §6 D13-a | Two-tier: self-service + admin | identity-user-management, authorization |
| §6 D13-b | Remove Stage 5 | authorization |
| §6 D13-c | UserProfile FK fix | identity-user-management |
| §2.1 | `user_profile.admin` permission | authorization |
