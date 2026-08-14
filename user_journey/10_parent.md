# Journey 10 — Parent

> **Role:** Parent
> **Scope:** Own institution — `institution_id` must match
> **Auth:** Supabase JWT with `user_tier: "institution"`

---

## Happy Paths

### HP-01: Login
```
POST /api/auth/login
Host: greenwood.localhost
Body: { email: "parent@greenwood.com", password: "..." }
→ 200 { access_token }
```

### HP-02: Read Own User Info
```
GET /api/v1/users/{parent_id}
→ 200 { id, email, name }
```

### HP-03: Read Own Profile
```
GET /api/v1/users/{parent_id}/profile
→ 200 { id, date_of_birth }
```

### HP-04: Update Own Profile
```
PATCH /api/v1/users/{parent_id}/profile
Body: { phone: "+1234567890" }
→ 200 { id, phone }
```

---

## Failure Scenarios

### FS-01: Parent tries to list users
```
GET /api/v1/users
Authorization: Bearer {parent_token}
→ 403 "Permission denied"
```
**Why:** Parent has `user.read` but only for own profile (Stage 3 bypass). List endpoint has no `owner_id`.

### FS-02: Parent tries to read another user
```
GET /api/v1/users/{other_user_id}
Authorization: Bearer {parent_token}
→ 403 "Permission denied"
```
**Why:** Parent has `user.read` but no `user_profile.admin`. Stage 3 bypass only works for own user_id.

### FS-03: Parent tries to create user
```
POST /api/v1/users
Authorization: Bearer {parent_token}
→ 403 "Permission denied"
```
**Why:** Parent has only `user.read`.

### FS-04: Parent tries to view homework
```
GET /api/v1/homeworks
Authorization: Bearer {parent_token}
→ 403 "Permission denied"
```
**Why:** Parent has no `homework.*` permissions.

### FS-05: Parent tries to view fees
```
GET /api/v1/fee-assignments
Authorization: Bearer {parent_token}
→ 403 "Permission denied"
```
**Why:** Parent has no `fee_assignment.*` permissions.

### FS-06: Parent tries to read another user's profile
```
GET /api/v1/users/{other_user_id}/profile
Authorization: Bearer {parent_token}
→ 403 "Permission denied"
```
**Why:** Parent has NO `user_profile.admin`.

---

## Notes

The Parent role is currently a **placeholder** for future functionality (C-02 Phase 2). The `parent_child_relationship` entity doesn't exist yet. When it does, Parent will be able to view their child's fees, homework, and grades.
