# Design — fix-user-profile-ownership

> **Change ID:** fix-user-profile-ownership
> **Capability:** C-02 Identity & User Management (intersecting C-04 Authorization)
> **Status:** Design
> **Created:** 2026-08-12
> **Decisional source:** D13 (UserProfile self-service & ownership)
> **Trace:** PRD §6, proposal §2, specs/identity-user-management, specs/authorization

---

## 1. Overview

This change fixes 5 Flow 16 issues with the UserProfile system: wrong FK target, missing permissions, and missing ownership enforcement. The design follows the established D12 pattern for cross-tier FK migration and the existing `_check_impl` ownership mechanism in `authz/dependencies.py`.

---

## 2. UserProfile FK Change

### 2.1 Current State

```
user_profile.user_id  ──FK──►  app_user.id
```

`UserProfile` model (`backend/kernel/user/models/user_profile.py:22`):
```python
user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), unique=True, nullable=False)
```

### 2.2 Target State

```
user_profile.user_id  ──FK──►  user_account.id
```

Model change:
```python
user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id"), unique=True, nullable=False)
```

Relationship change — `UserProfile.user` currently references the `User` (app_user) relationship. After the FK change, the relationship must be updated to reference `UserAccount` or removed (since `user_account` has no columns beyond `id`).

**Decision:** Keep the `user` relationship pointing to `User` (app_user) for backward compatibility in code that accesses `profile.user`. The FK is on `user_account.id` at the database level, but SQLAlchemy can still join `user_profile.user_id` to `app_user.id` since `app_user.id` is a subset of `user_account.id`. However, CD users (in `client_user`) won't have an `app_user` row, so `profile.user` will return `None` for CD users.

**Alternative considered:** Remove the relationship entirely. Rejected — too many callers depend on `profile.user`.

### 2.3 Migration Strategy (Migration 018)

Follow the exact D12 pattern from migration 015 (`backend/migrations/versions/015_user_account_parent_table.py`):

```python
# Step 1: Backfill user_account for existing profile user_ids
# For any user_profile.user_id that doesn't exist in user_account,
# insert a row. This handles edge cases where profiles exist but
# user_account rows were missed (shouldn't happen after 015, but
# defensive).
op.execute(
    "INSERT INTO user_account (id) SELECT DISTINCT up.user_id "
    "FROM user_profile up "
    "WHERE NOT EXISTS (SELECT 1 FROM user_account ua WHERE ua.id = up.user_id) "
    "ON CONFLICT (id) DO NOTHING"
)

# Step 2: Drop existing FK constraint
op.drop_constraint("user_profile_user_id_fkey", "user_profile", type_="foreignkey")

# Step 3: Create new FK to user_account
op.create_foreign_key(
    "user_profile_user_id_fkey",
    "user_profile",
    "user_account",
    ["user_id"],
    ["id"],
)
```

**Downgrade:** Reverse the FK back to `app_user.id`.

**Risk:** If any `user_profile.user_id` references a user that exists in `app_user` but NOT in `user_account`, the FK creation will fail. The backfill in Step 1 prevents this. Since migration 015 already backfilled all `app_user` rows into `user_account`, this is a safety net only.

---

## 3. Route Changes — Ownership Checks

### 3.1 Current Route Behavior

| Endpoint | Auth Check | Issue |
|----------|-----------|-------|
| `POST /api/v1/users/{user_id}/profile` | `Depends(require_permission("user_profile", "create"))` | No ownership check. Blocks everyone since no role has `user_profile.create`. |
| `GET /api/v1/users/{user_id}/profile` | `check_permission(ctx, enforcer, "user_profile", "read", ...)` | No ownership check. Any user with `user_profile.read` can read any profile. |
| `PATCH /api/v1/users/{user_id}/profile` | `check_permission(ctx, enforcer, "user_profile", "update", ...)` | No ownership check. Any user with `user_profile.update` can update any profile. |

### 3.2 Target Route Behavior

All three endpoints pass `owner_id=user_id` to the authorization dependency.

**POST endpoint:**
```python
@router.post("", ...)
def create_profile(
    user_id: uuid.UUID,
    dto: UserProfileCreateDTO,
    _authz: None = Depends(require_permission("user_profile", "create", owner_id=user_id)),  # <-- owner_id added
    ctx: TenantContext = Depends(get_tenant_context),
    svc: UserService = Depends(get_identity_user_service),
) -> UserProfileDTO:
```

**GET endpoint:**
```python
@router.get("", ...)
def get_profile(
    user_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    enforcer: Any = Depends(get_enforcer),
    svc: UserService = Depends(get_identity_user_service),
) -> UserProfileDTO:
    result = svc.get_profile(ctx, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Profile not found")
    check_permission(ctx, enforcer, "user_profile", "read",
        owner_id=user_id)  # <-- owner_id added, removed obj_client_id/obj_institution_id
    return result
```

**PATCH endpoint:**
```python
@router.patch("", ...)
def update_profile(
    user_id: uuid.UUID,
    dto: UserProfileUpdateDTO,
    ctx: TenantContext = Depends(get_tenant_context),
    enforcer: Any = Depends(get_enforcer),
    svc: UserService = Depends(get_identity_user_service),
) -> UserProfileDTO:
    user = svc.get_user(ctx, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    check_permission(ctx, enforcer, "user_profile", "update",
        owner_id=user_id)  # <-- owner_id added, removed obj_client_id/obj_institution_id
    try:
        return svc.update_profile(ctx, user_id, dto)
    except ValueError:
        raise HTTPException(status_code=404, detail="Profile not found")
```

**Why remove `obj_client_id` / `obj_institution_id`?** The ownership check is the primary gate. When `owner_id == ctx.user_id` (self-access), the check passes immediately without Casbin. When `owner_id != ctx.user_id` (admin accessing another user's profile), the admin bypass check uses the enforcer with the user's own scope — no need to pass the target user's client/institution. The existing `_check_impl` handles this correctly.

---

## 4. Self-Creation Logic

### 4.1 Problem

`POST /api/v1/users/{id}/profile` uses `Depends(require_permission("user_profile", "create"))`. The current `_check_impl` runs Casbin first, then ownership. A Teacher without `user_profile.create` permission fails at Casbin step before ownership is checked.

### 4.2 Solution — Reorder `_check_impl`

The current `_check_impl` flow:

```
1. Platform owner bypass
2. Role validation
3. Casbin check  ←── FAILS here for self-creation (no user_profile.create)
4. Ownership check  ←── never reached for self-creation
```

The new `_check_impl` flow:

```
1. Platform owner bypass
2. Role validation
3. Ownership check (self-access)  ←── PASSES here for self-creation
4. Casbin check (for non-self access)
5. Admin bypass ownership check (for non-self access)
```

**New `_check_impl` logic:**

```python
def _check_impl(ctx, enforcer, resource, action, *, obj_client_id=None,
                obj_institution_id=None, owner_id=None):
    # 1. Platform owner bypass
    if ctx.is_platform_owner or "platform_owner" in roles:
        return

    # 2. Role validation
    if not roles:
        raise HTTPException(403, "No roles assigned")

    # 3. Ownership check — self-access passes without Casbin
    if owner_id is not None and ctx.user_id and str(ctx.user_id) == str(owner_id):
        return  # Self-access: skip Casbin entirely

    # 4. Casbin check (for non-self access)
    sub = {"role": roles[0], ...}
    obj = {"name": resource, ...}
    if not enforcer.enforce(sub, obj, action):
        raise HTTPException(403, "Permission denied")

    # 5. Admin bypass for ownership (if owner_id was provided but wasn't self)
    # This is now redundant — Casbin already passed, which means the user
    # has the permission. No additional ownership gate needed for admins.
```

**Key insight:** After reordering, the ownership check is a **shortcut** for self-access (skip Casbin), not a **second gate**. If `owner_id != ctx.user_id`, the flow falls through to Casbin. If Casbin passes, the user has the permission (admin/institution scope) and can access the resource. If Casbin fails, 403.

This is **simpler** than the current two-gate design and correctly handles all scenarios:

| Scenario | owner_id == ctx.user_id? | Casbin passes? | Result |
|----------|-------------------------|----------------|--------|
| Teacher reads own profile | ✅ | (skipped) | 200 |
| Teacher reads other's profile | ❌ | ❌ (no cross-user perm) | 403 |
| Admin reads any profile | ❌ | ✅ (institution scope) | 200 |
| Student creates own profile | ✅ | (skipped) | 201 |
| Student creates other's profile | ❌ | ❌ (no user_profile.create) | 403 |
| Admin creates any profile | ❌ | ✅ (user_profile.create) | 201 |

---

## 5. Permission Changes

### 5.1 Current State (Migration 016)

| Role | user_profile.create | user_profile.read | user_profile.update |
|------|--------------------|--------------------|---------------------|
| Admin | ❌ (inserted in 016 but not mapped) | ✅ | ✅ |
| client_director | ❌ | ✅ | ✅ |
| institution_admin | ❌ | ❌ | ❌ |
| Teacher | ❌ | ❌ | ❌ |
| Staff | ❌ | ❌ | ❌ |
| Student | ❌ | ❌ | ❌ |
| Parent | ❌ | ❌ | ❌ |

**Note:** Migration 016 inserted the `user_profile.create` permission row but did NOT map it to any role. It also only mapped `user_profile.read` and `user_profile.update` to Admin and client_director.

### 5.2 Target State

| Role | user_profile.create | user_profile.read | user_profile.update |
|------|--------------------|--------------------|---------------------|
| Admin | ✅ (institution) | ✅ (institution) | ✅ (institution) |
| client_director | ✅ (tenant) | ✅ (tenant) | ✅ (tenant) |
| institution_admin | ✅ (institution) | ✅ (institution) | ✅ (institution) |
| Teacher | ❌ | ✅ (institution) | ✅ (institution) |
| Staff | ❌ | ✅ (institution) | ✅ (institution) |
| Student | ❌ | ✅ (institution) | ✅ (institution) |
| Parent | ❌ | ✅ (institution) | ✅ (institution) |

### 5.3 Migration 019 (Role-Permission Seed Data)

```python
# Admin, client_director, institution_admin: all three user_profile permissions
_admin_profile_perms = ["user_profile.create", "user_profile.read", "user_profile.update"]

# Teacher, Staff, Student, Parent: read + update only (no create)
_basic_profile_perms = ["user_profile.read", "user_profile.update"]
```

Insert with `ON CONFLICT (role_id, permission_id) DO NOTHING` for idempotency. Use the appropriate scope (`institution` or `tenant`) per role.

---

## 6. Ownership Check Integration with `check_permission`

### 6.1 Callers Affected

| Caller | Function | Change |
|--------|----------|--------|
| `POST /api/v1/users/{id}/profile` | `require_permission("user_profile", "create", owner_id=user_id)` | Add `owner_id` parameter |
| `GET /api/v1/users/{id}/profile` | `check_permission(ctx, enforcer, "user_profile", "read", owner_id=user_id)` | Add `owner_id` parameter |
| `PATCH /api/v1/users/{id}/profile` | `check_permission(ctx, enforcer, "user_profile", "update", owner_id=user_id)` | Add `owner_id` parameter |

### 6.2 No Other Callers Affected

All other `require_permission` and `check_permission` callers pass `owner_id=None` (the default). The reordering in `_check_impl` does not affect them — when `owner_id is None`, the self-access shortcut is skipped and Casbin runs first, preserving existing behavior.

### 6.3 Backward Compatibility

The `_check_impl` change is backward compatible:
- `owner_id=None` (all existing callers except profiles): behavior unchanged
- `owner_id=ctx.user_id` (self-access): passes immediately (new behavior for profiles)
- `owner_id!=ctx.user_id` (admin access): Casbin check runs (same as before, but now without the redundant second gate)

---

## 7. Files to Change

| File | Change |
|------|--------|
| `backend/kernel/user/models/user_profile.py` | FK `app_user.id` → `user_account.id` |
| `backend/kernel/authz/dependencies.py` | Reorder `_check_impl`: ownership check before Casbin |
| `backend/kernel/user/routes/profiles.py` | Add `owner_id=user_id` to all 3 endpoints |
| `backend/migrations/versions/018_fix_user_profile_fk.py` | **New** — FK migration + backfill |
| `backend/migrations/versions/019_user_profile_permissions.py` | **New** — role-permission seed data |
| `backend/tests/test_c02_user.py` | Add ownership + self-creation test scenarios |

---

## 8. Test Plan

### 8.1 New Test Scenarios

| ID | Scenario | Expected |
|----|----------|----------|
| T-1 | Teacher creates own profile (POST with owner_id == ctx.user_id) | 201 |
| T-2 | Teacher reads own profile (GET with owner_id == ctx.user_id) | 200 |
| T-3 | Teacher updates own profile (PATCH with owner_id == ctx.user_id) | 200 |
| T-4 | Teacher reads another teacher's profile (owner_id != ctx.user_id) | 403 |
| T-5 | Teacher updates another teacher's profile | 403 |
| T-6 | Teacher creates profile for another user | 403 |
| T-7 | Admin reads any profile (institution scope bypass) | 200 |
| T-8 | Admin updates any profile | 200 |
| T-9 | Admin creates profile for any user | 201 |
| T-10 | Duplicate profile creation (POST when profile exists) | 409 |
| T-11 | CD user has a UserProfile (FK fix) | 201 |

### 8.2 Migration Tests

| ID | Scenario | Expected |
|----|----------|----------|
| MT-1 | Migration 018 applies cleanly | No errors |
| MT-2 | Migration 018 backfills user_account for existing profiles | All profile user_ids have user_account rows |
| MT-3 | Migration 019 inserts user_profile.create permission | Row exists |
| MT-4 | Migration 019 maps permissions to all roles | Correct rows in role_permission |
| MT-5 | Migration 019 is idempotent (run twice) | No duplicates |

---

## 9. Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| `_check_impl` reordering breaks existing callers | **High** | All existing callers pass `owner_id=None`, which skips the ownership shortcut. Behavior is identical. Verify with existing test suite. |
| Migration 018 fails if user_profile.user_id has orphaned values | **Low** | Backfill step runs first. Since migration 015 already backfilled all app_user rows into user_account, orphans are unlikely. |
| `UserProfile.user` relationship breaks for CD users | **Medium** | CD users have no `app_user` row, so `profile.user` returns `None`. Document this. Callers should use `profile.user_id` directly. |
| Self-creation bypass could be exploited | **Low** | `owner_id` check ensures only the authenticated user can create their own profile. The `user_id` comes from the URL path, not the request body. |

---

## 10. Implementation Order

1. **Migration 018** — FK change + backfill (schema change first)
2. **Model update** — `user_profile.py` FK target
3. **`_check_impl` reorder** — ownership before Casbin
4. **Route changes** — add `owner_id` to all 3 endpoints
5. **Migration 019** — role-permission seed data
6. **Tests** — new scenarios + verify existing tests pass
