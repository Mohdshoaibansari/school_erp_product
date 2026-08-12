# Proposal — fix-user-profile-ownership

> **Change ID:** fix-user-profile-ownership
> **Capability:** C-02 Identity & User Management (intersecting C-04 Authorization)
> **Delta type:** MODIFIED
> **Status:** Proposal
> **Created:** 2026-08-12

---

## 1. Problem Summary

Flow 16 testing revealed 5 issues with the UserProfile system:

1. `UserProfile.user_id` FK → `app_user.id` prevents CD users (in `client_user`) from having profiles
2. No role has `user_profile.create` permission — `POST /api/v1/users/{id}/profile` returns 403 for everyone
3. No ownership check on profile endpoints — any user with `user_profile.update` can update any other user's profile
4. Teacher/Staff/Student/Parent don't have `user_profile.update` — users can't update their own profile
5. No ownership check on profile read — any user with `user_profile.read` can see any profile

---

## 2. Proposed Changes

### 2.1 Identity & User Management (C-02) — MODIFIED

| Change | Description | Key Decision |
|--------|-------------|--------------|
| UserProfile FK fix | `UserProfile.user_id` FK references `user_account.id` instead of `app_user.id` | D13-c |
| Ownership enforcement on profile routes | Profile endpoints pass `owner_id=user_id` to `check_permission`. Self-access passes; non-admin access to others' profiles is blocked | D13-a |
| Self-creation logic | `POST /api/v1/users/{id}/profile` allows self-creation without `user_profile.create` permission via owner_id check | D13-b |

### 2.2 Authorization (C-04) — MODIFIED

| Change | Description | Key Decision |
|--------|-------------|--------------|
| `user_profile.create` for admin roles | Added for Admin, client_director, institution_admin with institution scope | D13 |
| `user_profile.update` for all roles | Added for Teacher, Staff, Student, Parent with institution scope | D13 |
| `user_profile.read` for all roles | Added for Teacher, Staff, Student, Parent with institution scope | D13 |

---

## 3. Scope Boundaries

### In Scope
- UserProfile FK migration from `app_user.id` to `user_account.id`
- Ownership checks on all profile endpoints (GET, POST, PATCH)
- Self-creation bypass for `user_profile.create` permission
- Role-permission mappings for `user_profile.create`, `user_profile.update`, `user_profile.read`
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
| AC-2 | All roles have `user_profile.read` and `user_profile.update` permissions |
| AC-3 | Admin/CD/institution_admin have `user_profile.create` permission |
| AC-4 | `POST /api/v1/users/{id}/profile` allows self-creation without `user_profile.create` (owner_id check) |
| AC-5 | `PATCH /api/v1/users/{id}/profile` passes `owner_id=user_id` — self-only for non-admin |
| AC-6 | `GET /api/v1/users/{id}/profile` passes `owner_id=user_id` — self-only for non-admin |
| AC-7 | Admin can create/update any profile (institution scope bypass) |
| AC-8 | CD user (in `client_user`) can have a UserProfile (FK fix) |

---

## 5. Traceability

| PRD Section | Key Decision | Spec Domain |
|-------------|--------------|-------------|
| §6 D13-a | Self-only ownership | identity-user-management |
| §6 D13-b | Self-creation without permission | identity-user-management |
| §6 D13-c | UserProfile FK fix | identity-user-management |
| §2.1 | Role-permission mappings | authorization |
