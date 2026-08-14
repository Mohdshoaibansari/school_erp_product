# Journey 08 — Staff

> **Role:** Staff
> **Scope:** Own institution — `institution_id` must match
> **Auth:** Supabase JWT with `user_tier: "institution"`

---

## Happy Paths

### HP-01: Login
```
POST /api/auth/login
Host: greenwood.localhost
Body: { email: "staff@greenwoodhigh.com", password: "..." }
→ 200 { access_token }
```

### HP-02: List Users (read-only)
```
GET /api/v1/users
→ 200 [{ id, email, name }, ...]
```

### HP-03: Update Own Profile
```
PATCH /api/v1/users/{staff_id}/profile
Body: { photo: "https://..." }
→ 200 { id, photo }
```

### HP-04: Read Own Profile
```
GET /api/v1/users/{staff_id}/profile
→ 200 { id, date_of_birth }
```

### HP-05: Read Fee Assignments
```
GET /api/v1/fee-assignments
→ 200 [{ id, amount, status }, ...]
```

---

## Failure Scenarios

### FS-01: Staff tries to create user
```
POST /api/v1/users
Authorization: Bearer {staff_token}
→ 403 "Permission denied"
```
**Why:** Staff has `user.read/update` but NOT `user.create`.

### FS-02: Staff tries to create homework
```
POST /api/v1/homeworks
Authorization: Bearer {staff_token}
→ 403 "Permission denied"
```
**Why:** Staff has no `homework.*` permissions.

### FS-03: Staff tries to manage fees
```
POST /api/v1/fee-assignments
Authorization: Bearer {staff_token}
→ 403 "Permission denied"
```
**Why:** Staff has `fee_assignment.read` but NOT `fee_assignment.create`.

### FS-04: Staff tries to read another user's profile
```
GET /api/v1/users/{other_user_id}/profile
Authorization: Bearer {staff_token}
→ 403 "Permission denied"
```
**Why:** Staff has NO `user_profile.admin`.

### FS-05: Staff tries to manage org units
```
POST /api/v1/org-units
Authorization: Bearer {staff_token}
→ 403 "Permission denied"
```
**Why:** Staff has no `org_unit.*` permissions.
