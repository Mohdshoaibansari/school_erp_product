# Journey 09 — Student

> **Role:** Student
> **Scope:** Own institution — `institution_id` must match
> **Auth:** Supabase JWT with `user_tier: "institution"`

---

## Happy Paths

### HP-01: Login
```
POST /api/auth/login
Host: greenwood.localhost
Body: { email: "student@greenwoodhigh.com", password: "..." }
→ 200 { access_token }
```

### HP-02: View Homework
```
GET /api/v1/homeworks
→ 200 [{ id, title, subject, due_date }, ...]
```

### HP-03: Submit Homework
```
POST /api/v1/submissions
Body: { homework_id: "...", content: "Completed all problems" }
→ 201 { id, homework_id, status: "submitted" }
```

### HP-04: View Own Submissions
```
GET /api/v1/submissions
→ 200 [{ id, homework_id, status, score }, ...]
```

### HP-05: View Grades
```
GET /api/v1/submissions/{sub_id}
→ 200 { id, status: "graded", score: 42, feedback: "Good work!" }
```

### HP-06: View Fee Assignments
```
GET /api/v1/fee-assignments
→ 200 [{ id, amount, status, due_date }, ...]
```

### HP-07: View Payments
```
GET /api/v1/payments
→ 200 [{ id, amount, payment_method }, ...]
```

### HP-08: Read Own Profile
```
GET /api/v1/users/{student_id}/profile
→ 200 { id, date_of_birth, gender }
```

### HP-09: Update Own Profile
```
PATCH /api/v1/users/{student_id}/profile
Body: { blood_group: "B+" }
→ 200 { id, blood_group }
```

### HP-10: Read Own User Info
```
GET /api/v1/users/{student_id}
→ 200 { id, email, name }
```

---

## Failure Scenarios

### FS-01: Student tries to create user
```
POST /api/v1/users
Authorization: Bearer {student_token}
→ 403 "Permission denied"
```
**Why:** Student has `user.read` but NOT `user.create`.

### FS-02: Student tries to create homework
```
POST /api/v1/homeworks
Authorization: Bearer {student_token}
→ 403 "Permission denied"
```
**Why:** Student has `homework.read` but NOT `homework.create`.

### FS-03: Student tries to grade submission
```
POST /api/v1/submissions/{sub_id}/grade
Authorization: Bearer {student_token}
→ 403 "Permission denied"
```
**Why:** Student has no `grade.*` permissions.

### FS-04: Student tries to read another user's profile
```
GET /api/v1/users/{other_user_id}/profile
Authorization: Bearer {student_token}
→ 403 "Permission denied"
```
**Why:** Student has NO `user_profile.admin`.

### FS-05: Student tries to manage fees
```
POST /api/v1/fee-assignments
Authorization: Bearer {student_token}
→ 403 "Permission denied"
```
**Why:** Student has `fee_assignment.read` but NOT `fee_assignment.create`.

### FS-06: Student tries to update another user
```
PATCH /api/v1/users/{other_user_id}
Authorization: Bearer {student_token}
Body: { name: "Hacked" }
→ 403 "Permission denied"
```
**Why:** Student has `user.read` but NOT `user.update` (only for own profile via Stage 3 bypass).
