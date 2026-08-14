# Journey 07 — Teacher

> **Role:** Teacher
> **Scope:** Own institution — `institution_id` must match
> **Auth:** Supabase JWT with `user_tier: "institution"`

---

## Happy Paths

### HP-01: Login
```
POST /api/auth/login
Host: greenwood.localhost
Body: { email: "teacher@greenwoodhigh.com", password: "..." }
→ 200 { access_token }
```

### HP-02: Create Homework
```
POST /api/v1/homeworks
Body: { title: "Math Worksheet", institution_id: "...", subject: "Mathematics", grade_level: "Grade 5", due_date: "2026-09-15" }
→ 201 { id, title }
```

### HP-03: Update Homework
```
PATCH /api/v1/homeworks/{hw_id}
Body: { title: "Updated Title" }
→ 200 { id, title }
```

### HP-04: Delete Homework
```
DELETE /api/v1/homeworks/{hw_id}
→ 204
```

### HP-05: Close Homework
```
POST /api/v1/homeworks/{hw_id}/close
→ 200 { id, status: "closed" }
```

### HP-06: Read Submissions
```
GET /api/v1/submissions?homework_id={hw_id}
→ 200 [{ id, student_id, content }, ...]
```

### HP-07: Grade Submission
```
POST /api/v1/submissions/{sub_id}/grade
Body: { score: 42, feedback: "Good work!" }
→ 201 { id, score, feedback }
```

### HP-08: Update Grade
```
PATCH /api/v1/submissions/{sub_id}/grade/{grade_id}
Body: { score: 45 }
→ 200 { id, score }
```

### HP-09: List Users (read-only)
```
GET /api/v1/users
→ 200 [{ id, email, name }, ...]
```

### HP-10: Update Own Profile
```
PATCH /api/v1/users/{teacher_id}/profile
Body: { photo: "https://..." }
→ 200 { id, photo }
```

### HP-11: Read Own Profile
```
GET /api/v1/users/{teacher_id}/profile
→ 200 { id, date_of_birth, gender }
```

---

## Failure Scenarios

### FS-01: Teacher tries to create user
```
POST /api/v1/users
Authorization: Bearer {teacher_token}
→ 403 "Permission denied"
```
**Why:** Teacher has `user.read/update` but NOT `user.create`.

### FS-02: Teacher tries to manage fees
```
POST /api/v1/fee-assignments
Authorization: Bearer {teacher_token}
→ 403 "Permission denied"
```
**Why:** Teacher has `fee_assignment.read` but NOT `fee_assignment.create`.

### FS-03: Teacher tries to read another user's profile
```
GET /api/v1/users/{other_user_id}/profile
Authorization: Bearer {teacher_token}
→ 403 "Permission denied"
```
**Why:** Teacher has NO `user_profile.admin`. Self-read works (Stage 3), but reading others fails.

### FS-04: Teacher tries to manage org units
```
POST /api/v1/org-units
Authorization: Bearer {teacher_token}
→ 403 "Permission denied"
```
**Why:** Teacher has no `org_unit.*` permissions.

### FS-05: Teacher tries to suspend user
```
POST /api/v1/users/{user_id}/transition
Authorization: Bearer {teacher_token}
→ 403 "Permission denied"
```
**Why:** Teacher has `user.read/update` but NOT `user.suspend`.

### FS-06: Teacher tries to create homework for another institution
```
POST /api/v1/homeworks
Authorization: Bearer {teacher_token}
Body: { institution_id: "{other_institution_id}", ... }
→ 403 "Permission denied" (Casbin: institution scope check fails)
```
**Why:** Teacher's `institution_id` doesn't match the target institution.
