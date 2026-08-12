# PRD — UserProfile Self-Service & Ownership

> **Capability:** C-02 Identity & User Management
> **Decisional source:** D13 (ADR)

## Problem

UserProfile system has 5 issues:
1. CD users can't have profiles (FK to `app_user`)
2. No role has `user_profile.create` permission
3. No ownership check — any user with permission can access any profile
4. Teacher/Staff/Student/Parent can't update own profile
5. No ownership check on profile read

## Goal

Any authenticated user can create/read/update their own profile. Admins can manage any profile.

## Acceptance Criteria

| ID | Criterion |
|---|---|
| AC-1 | `UserProfile.user_id` FK references `user_account.id` |
| AC-2 | All roles have `user_profile.read` and `user_profile.update` |
| AC-3 | Admin/CD/institution_admin have `user_profile.create` |
| AC-4 | Profile endpoints pass `owner_id=user_id` to `check_permission` |
| AC-5 | Teacher can update own profile but not another's |
| AC-6 | Admin can update any profile |
