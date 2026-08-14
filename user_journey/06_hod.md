# Journey 06 — HOD (Head of Department)

> **Role:** HOD
> **Scope:** Own institution — `institution_id` must match
> **Auth:** Supabase JWT with `user_tier: "institution"`

---

## Happy Paths

### HP-01: Login
```
POST /api/auth/login
Host: greenwood.localhost
Body: { email: "hod@greenwoodhigh.com", password: "..." }
→ 200 { access_token }
```

### HP-02: List Users (read-only)
```
GET /api/v1/users
→ 200 [{ id, email, name }, ...]
```

### HP-03: Read Role Assignments
```
GET /api/v1/users/{user_id}/roles
→ 200 [{ id, role_id }, ...]
```

### HP-04: Update Org Unit
```
PATCH /api/v1/org-units/{ou_id}
Body: { name: "Updated Department" }
→ 200 { id, name }
```

### HP-05: Read Fee Assignments
```
GET /api/v1/fee-assignments
→ 200 [{ id, amount, status }, ...]
```

### HP-06: Read Homework
```
GET /api/v1/homeworks
→ 200 [{ id, title, subject }, ...]
```

### HP-07: Read Submissions
```
GET /api/v1/submissions
→ 200 [{ id, homework_id, student_id }, ...]
```

---

## Failure Scenarios

### FS-01: HOD tries to create user
```
POST /api/v1/users
Authorization: Bearer {hod_token}
→ 403 "Permission denied"
```
**Why:** HOD has `user.read` but NOT `user.create`.

### FS-02: HOD tries to create homework
```
POST /api/v1/homeworks
Authorization: Bearer {hod_token}
→ 403 "Permission denied"
```
**Why:** HOD has `homework.read` but NOT `homework.create`.

### FS-03: HOD tries to create fee type
```
POST /api/v1/fee-types
Authorization: Bearer {hod_token}
→ 403 "Permission denied"
```
**Why:** HOD has no `fee.*` permissions.

### FS-04: HOD tries to read another user's profile
```
GET /api/v1/users/{other_user_id}/profile
Authorization: Bearer {hod_token}
→ 403 "Permission denied"
```
**Why:** HOD has NO `user_profile.admin` permission.
