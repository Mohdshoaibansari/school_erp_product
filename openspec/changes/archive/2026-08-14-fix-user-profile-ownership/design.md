# Design — fix-user-profile-ownership

> **Change ID:** fix-user-profile-ownership
> **Capability:** C-02 Identity & User Management (intersecting C-04 Authorization)
> **Status:** Design
> **Created:** 2026-08-12
> **Last updated:** 2026-08-13
> **Decisional source:** D13 (UserProfile self-service & admin management)
> **Trace:** PRD §6, proposal §2, specs/identity-user-management, specs/authorization

---

## 1. Overview

This change fixes 5 Flow 16 issues with the UserProfile system using a two-tier permission model:

1. **Self-service (Stage 3):** Any user can manage their own profile — `owner_id == ctx.user_id` bypasses Casbin entirely
2. **Admin management (Stage 4):** Admin/CD/institution_admin can manage any profile via `user_profile.admin` permission checked in Casbin

Stage 5 (ownership check) is removed from `_check_impl` — it is no longer needed.

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

Keep the `user` relationship pointing to `User` (app_user) for backward compatibility. CD users (in `client_user`) won't have an `app_user` row, so `profile.user` will return `None` for CD users. Callers should use `profile.user_id` directly.

### 2.3 Migration Strategy (Migration 018)

Follow the D12 pattern from migration 015:

```python
# Step 1: Backfill user_account for existing profile user_ids
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

---

## 3. Authorization Flow — Two-Tier Model

### 3.1 New `_check_impl` Flow

```
1. Platform owner bypass
2. Role validation
3. Self-service bypass (Stage 3)
   → if owner_id is not None AND owner_id == ctx.user_id → PASS (skip Casbin)
4. Casbin enforcement (Stage 4)
   → check enforcer.enforce(sub, obj, action) → PASS or 403
```

**Stage 5 (ownership/admin bypass) is DELETED.** There is no stage after Casbin.

### 3.2 `_check_impl` Implementation

```python
def _check_impl(ctx, enforcer, resource, action, *, obj_client_id=None,
                obj_institution_id=None, owner_id=None):
    # 1. Platform owner bypass
    if ctx.is_platform_owner or "platform_owner" in roles:
        return

    # 2. Role validation
    if not roles:
        raise HTTPException(403, "No roles assigned")

    # 3. Self-service bypass — owner matches authenticated user
    if owner_id is not None and ctx.user_id and str(ctx.user_id) == str(owner_id):
        return  # Self-access: skip Casbin entirely

    # 4. Casbin enforcement (for non-self access)
    sub = {"role": roles[0], ...}
    obj = {"name": resource, ...}
    if not enforcer.enforce(sub, obj, action):
        raise HTTPException(403, "Permission denied")

    # NO Stage 5 — Casbin result is authoritative
```

### 3.3 Scenario Matrix

| Scenario | owner_id == ctx.user_id? | Stage 3 | Casbin `user_profile.admin` | Result |
|----------|-------------------------|---------|----------------------------|--------|
| Teacher reads own profile | ✅ | PASS | (skipped) | 200 |
| Teacher reads other's profile | ❌ | skip | ❌ | 403 |
| Admin reads any profile | ❌ | skip | ✅ (institution) | 200 |
| Student creates own profile | ✅ | PASS | (skipped) | 201 |
| Student creates other's profile | ❌ | skip | ❌ | 403 |
| CD creates any profile | ❌ | skip | ✅ (tenant) | 201 |
| Parent updates own profile | ✅ | PASS | (skipped) | 200 |
| institution_admin updates any | ❌ | skip | ✅ (institution) | 200 |

### 3.4 Backward Compatibility

All existing callers pass `owner_id=None` (the default). When `owner_id is None`, Stage 3 is skipped and Casbin runs first — identical to the current behavior. The change is fully backward compatible.

---

## 4. Route Changes

### 4.1 Profile Endpoints

All three endpoints pass `owner_id=user_id` and use `user_profile.admin` as the Casbin action for non-self access.

**POST endpoint:**
```python
@router.post("", ...)
def create_profile(
    user_id: uuid.UUID,
    dto: UserProfileCreateDTO,
    _authz: None = Depends(require_permission("user_profile", "admin", owner_id=user_id)),
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
    check_permission(ctx, enforcer, "user_profile", "admin", owner_id=user_id)
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
    check_permission(ctx, enforcer, "user_profile", "admin", owner_id=user_id)
    try:
        return svc.update_profile(ctx, user_id, dto)
    except ValueError:
        raise HTTPException(status_code=404, detail="Profile not found")
```

**Key:** The action is `"admin"` (not `"create"`/`"read"`/`"update"`). Stage 3 handles self-service; Stage 4 checks `user_profile.admin` for non-self access.

---

## 5. Permission Changes

### 5.1 New Permission: `user_profile.admin`

A single `user_profile.admin` permission replaces the per-action permissions for non-self access. This simplifies the model: one permission governs all admin-level profile operations.

### 5.2 Role-Permission Mapping (Migration 019)

| Role | `user_profile.admin` | Scope |
|------|---------------------|-------|
| Admin | ✅ | institution |
| client_director | ✅ | tenant |
| institution_admin | ✅ | institution |
| Teacher | ❌ | — |
| Staff | ❌ | — |
| Student | ❌ | — |
| Parent | ❌ | — |

Teacher/Staff/Student/Parent do NOT need any `user_profile.*` permission — they use Stage 3 self-service bypass.

---

## 6. Files to Change

| File | Change |
|------|--------|
| `backend/kernel/user/models/user_profile.py` | FK `app_user.id` → `user_account.id` |
| `backend/kernel/authz/dependencies.py` | Remove Stage 5, keep Stage 3 + Stage 4 only |
| `backend/kernel/user/routes/profiles.py` | All 3 endpoints: pass `owner_id=user_id`, action=`"admin"` |
| `backend/migrations/versions/018_fix_user_profile_fk.py` | **New** — FK migration + backfill |
| `backend/migrations/versions/019_user_profile_admin_permission.py` | **New** — `user_profile.admin` permission + role mappings |
| `backend/tests/test_c02_user.py` | Add self-service + admin test scenarios |

---

## 7. Test Plan

### 7.1 New Test Scenarios

| ID | Scenario | Expected |
|----|----------|----------|
| T-1 | Teacher creates own profile (Stage 3 bypass) | 201 |
| T-2 | Teacher reads own profile (Stage 3 bypass) | 200 |
| T-3 | Teacher updates own profile (Stage 3 bypass) | 200 |
| T-4 | Teacher reads another teacher's profile | 403 |
| T-5 | Teacher updates another teacher's profile | 403 |
| T-6 | Teacher creates profile for another user | 403 |
| T-7 | Admin reads any profile (`user_profile.admin`) | 200 |
| T-8 | Admin updates any profile (`user_profile.admin`) | 200 |
| T-9 | Admin creates profile for any user (`user_profile.admin`) | 201 |
| T-10 | Duplicate profile creation (POST when profile exists) | 409 |
| T-11 | CD user has a UserProfile (FK fix) | 201 |

### 7.2 Migration Tests

| ID | Scenario | Expected |
|----|----------|----------|
| MT-1 | Migration 018 applies cleanly | No errors |
| MT-2 | Migration 018 backfills user_account for existing profiles | All profile user_ids have user_account rows |
| MT-3 | Migration 019 inserts `user_profile.admin` permission | Row exists |
| MT-4 | Migration 019 maps `user_profile.admin` to Admin/CD/institution_admin | Correct rows in role_permission |
| MT-5 | Migration 019 is idempotent (run twice) | No duplicates |

---

## 8. Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Removing Stage 5 affects other resources | **Low** | Stage 5 only ran when `owner_id` was set. Only profile routes pass `owner_id`. Other resources unaffected. |
| Migration backfill for existing profiles | **Low** | Migration 015 already backfilled all `app_user` rows into `user_account`. Migration 018 backfill is a safety net. |
| `UserProfile.user` relationship breaks for CD users | **Medium** | CD users have no `app_user` row, so `profile.user` returns `None`. Document this. |
| Self-service bypass could be exploited | **Low** | `owner_id` check ensures only the authenticated user can access their own profile. `user_id` comes from URL path, not request body. |

---

## 9. Implementation Order

1. **Migration 018** — FK change + backfill (schema change first)
2. **Model update** — `user_profile.py` FK target
3. **`_check_impl` update** — Remove Stage 5, keep Stage 3 + Stage 4
4. **Route changes** — Add `owner_id=user_id`, action=`"admin"` to all 3 endpoints
5. **Migration 019** — `user_profile.admin` permission + role mappings
6. **Tests** — New scenarios + verify existing tests pass
