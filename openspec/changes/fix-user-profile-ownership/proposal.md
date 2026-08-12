# Proposal — UserProfile Self-Service & Ownership

## Why

Flow 16 testing revealed 5 problems with the UserProfile system:
1. `UserProfile.user_id` FK → `app_user.id` — CD users can't have profiles
2. No role has `user_profile.create` — permission exists but isn't assigned
3. No ownership check — any user with permission can access any profile
4. Teacher/Staff/Student/Parent can't update own profile
5. No ownership check on profile read

## What Changes

- **Schema**: `UserProfile.user_id` FK → `user_account.id` (D12 pattern)
- **Permissions**: Add `user_profile.create` for Admin/CD/institution_admin; add `user_profile.update` and `user_profile.read` for all roles
- **Routes**: All 3 profile endpoints pass `owner_id=user_id` to `check_permission`
- **Behavior**: Any user can create/update/read their own profile; admins can manage any profile

## Capabilities

- **identity-user-management (MODIFIED)** — UserProfile FK, routes, ownership check
- **authorization (MODIFIED)** — role-permission mappings for user_profile
