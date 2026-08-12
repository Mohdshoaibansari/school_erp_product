# UserProfile System — Analysis & Design

> **Date:** 2026-08-12
> **Status:** Analysis — pending implementation
> **Source:** Flow 16 testing revealed permission gaps

---

## 1. Current State

### Model
```python
# backend/kernel/user/models/user_profile.py
class UserProfile(Base):
    __tablename__ = "user_profile"
    id: UUID PK
    user_id: UUID FK → app_user.id  ← PROBLEM: CD users in client_user can't have profiles
    photo: str | None
    date_of_birth: date | None
    gender: str | None
    blood_group: str | None
```

### Routes (`backend/kernel/user/routes/profiles.py`)

| Endpoint | Permission | Ownership Check | Issue |
|---|---|---|---|
| `POST /users/{id}/profile` | `user_profile.create` | None | No role has this permission |
| `GET /users/{id}/profile` | `user_profile.read` (inline) | None | Any user with read can see any profile |
| `PATCH /users/{id}/profile` | `user_profile.update` (inline) | None | Any user with update can update any profile |

### Permission Gaps

| Role | Has `user_profile.create` | Has `user_profile.update` | Can update own profile? |
|---|---|---|---|
| Admin | ❌ | ✅ | ✅ (admin bypass) |
| client_director | ❌ | ✅ | ✅ (admin bypass) |
| institution_admin | ❌ | ✅ | ✅ (admin bypass) |
| Teacher | ❌ | ❌ | ❌ |
| Staff | ❌ | ❌ | ❌ |
| Student | ❌ | ❌ | ❌ |
| Parent | ❌ | ❌ | ❌ |

---

## 2. Problems

### Problem 1: `UserProfile.user_id` FK → `app_user.id`
CD users (in `client_user`) can't have profiles. Same FK pattern as `login_attempt`, `role_assignment`, `fee_assignment`.

**Fix:** Change FK to `user_account.id` (same as D12).

### Problem 2: No role has `user_profile.create`
The permission exists in the `permission` table but no role has it in `role_permission`. The `create_profile` route requires this permission → 403 for everyone.

**Fix:** Add `user_profile.create` for Admin, CD, institution_admin (who create profiles on behalf of users).

### Problem 3: No ownership check on profile update
The `update_profile` route uses `check_permission` with ABAC (client/institution scope) but does NOT pass `owner_id`. Any user with `user_profile.update` can update any other user's profile.

**Fix:** Pass `owner_id=user_id` to `check_permission`. This restricts updates to:
- The user themselves (owner_id matches)
- Admin/institution_admin (admin scope bypass)

### Problem 4: Teacher/Staff/Student/Parent can't update own profile
These roles don't have `user_profile.update`. Any user should be able to update their own profile.

**Fix:** Add `user_profile.update` for all roles.

### Problem 5: No ownership check on profile read
The `get_profile` route uses `check_permission` with ABAC but no `owner_id`. Any user with `user_profile.read` can see any profile.

**Fix:** Pass `owner_id=user_id` to restrict reads to self + admin.

---

## 3. Recommended Fix

### Schema changes
- `UserProfile.user_id` FK → `user_account.id` (migration)
- `user_profile.create` added for Admin, CD, institution_admin (migration)
- `user_profile.update` added for Teacher, Staff, Student, Parent (migration)

### Code changes
- `profiles.py`: All 3 endpoints pass `owner_id=user_id` to `check_permission`
- `profiles.py`: `create_profile` uses inline `check_permission` (same pattern as other routes)

### Permission matrix after fix

| Role | create | read | update | Notes |
|---|---|---|---|---|
| Admin | ✅ | ✅ | ✅ | Admin bypass — any profile |
| client_director | ✅ | ✅ | ✅ | Admin bypass — any profile in tenant |
| institution_admin | ✅ | ✅ | ✅ | Admin bypass — any profile in institution |
| Teacher | ❌ | ✅ (self) | ✅ (self) | Ownership check restricts to own |
| Staff | ❌ | ✅ (self) | ✅ (self) | Ownership check restricts to own |
| Student | ❌ | ✅ (self) | ✅ (self) | Ownership check restricts to own |
| Parent | ❌ | ✅ (self) | ✅ (self) | Ownership check restricts to own |

---

## 4. Implementation Checklist

- [ ] Migration: `UserProfile.user_id` FK → `user_account.id`
- [ ] Migration: Add `user_profile.create` for Admin, CD, institution_admin
- [ ] Migration: Add `user_profile.update` for Teacher, Staff, Student, Parent
- [ ] Migration: Add `user_profile.read` for Teacher, Staff, Student, Parent (if not already)
- [ ] Code: `create_profile` — inline `check_permission` with `owner_id=user_id`
- [ ] Code: `get_profile` — pass `owner_id=user_id` to `check_permission`
- [ ] Code: `update_profile` — pass `owner_id=user_id` to `check_permission`
- [ ] Test: CD can create profile for student
- [ ] Test: Teacher can update own profile
- [ ] Test: Teacher cannot update another teacher's profile
- [ ] Test: Admin can update any profile
