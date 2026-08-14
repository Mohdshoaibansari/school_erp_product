# Journey 05 — Principal

> **Role:** Principal
> **Scope:** Own institution — `institution_id` must match
> **Auth:** Supabase JWT with `user_tier: "institution"`

---

## Happy Paths

### HP-01: Login
```
POST /api/auth/login
Host: greenwood.localhost
Body: { email: "principal@greenwoodhigh.com", password: "..." }
→ 200 { access_token, user_tier: "institution" }
```

### HP-02: Read Institution
```
GET /api/v1/institutions/{inst_id}
→ 200 { id, display_name }
```

### HP-03: Update Institution
```
PATCH /api/v1/institutions/{inst_id}
Body: { display_name: "Updated Name" }
→ 200 { id, display_name }
```

### HP-04: Create Org Unit
```
POST /api/v1/org-units
Body: { ... }
→ 201 { id }
```

### HP-05: Delete Org Unit
```
DELETE /api/v1/org-units/{ou_id}
→ 204
```

### HP-06: List Users (read-only)
```
GET /api/v1/users
→ 200 [{ id, email, name }, ...]
```

### HP-07: Read Role Assignments
```
GET /api/v1/users/{user_id}/roles
→ 200 [{ id, role_id }, ...]
```

---

## Failure Scenarios

### FS-01: Principal tries to create user
```
POST /api/v1/users
Authorization: Bearer {principal_token}
→ 403 "Permission denied"
```
**Why:** Principal has `user.read` but NOT `user.create`.

### FS-02: Principal tries to manage fees
```
POST /api/v1/fee-types
Authorization: Bearer {principal_token}
→ 403 "Permission denied"
```
**Why:** Principal has `fee.read` but NOT `fee.create`.

### FS-03: Principal tries to suspend user
```
POST /api/v1/users/{user_id}/transition
Authorization: Bearer {principal_token}
→ 403 "Permission denied"
```
**Why:** Principal has `user.read` but NOT `user.suspend`.

### FS-04: Principal tries to read another user's profile
```
GET /api/v1/users/{other_user_id}/profile
Authorization: Bearer {principal_token}
→ 403 "Permission denied"
```
**Why:** Principal has NO `user_profile.admin` permission. Self-read works (Stage 3 bypass), but reading others fails.

### FS-05: Principal tries to manage config
```
GET /api/v1/config/keys
Authorization: Bearer {principal_token}
→ 403 "Permission denied"
```
**Why:** Principal has no config permissions.
