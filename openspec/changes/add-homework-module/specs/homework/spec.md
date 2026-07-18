# Homework Module — Specification

> **Domain:** `homework`  
> **Classification:** ADDED  
> **Tier:** Business  
> **Depends on:** C-01 (tenant isolation), C-02 (teacher/student identity), C-04 (authorization), C-11 (audit)

---

## HW-1: Homework Management

### HW-1.1: Create Homework
A Teacher can create a homework assignment with title, description, subject, grade_level, section, due_date, max_score. The homework is tenant-scoped (client_id auto-injected from TenantContext).

**Acceptance:**
- `POST /api/v1/homeworks` with `{ title, description?, subject, grade_level, section, due_date, max_score? }` returns 201 with HomeworkDTO.
- `client_id` and `institution_id` are auto-injected from TenantContext.
- `assigned_by` is set to `ctx.user_id`.
- Status starts as `active`.

### HW-1.2: List Homeworks
List all homeworks. Supports optional `?grade_level=`, `?subject=`, `?status=` filters. Students see only homeworks matching their own grade_level + section.

**Acceptance:**
- `GET /api/v1/homeworks` returns list of HomeworkDTO.
- Tenant-filtered: shows only homeworks for the user's institution.
- Student filter: only homeworks where `grade_level` and `section` match the student's profile.

### HW-1.3: Get Homework
Get a single homework by ID with submission count.

**Acceptance:**
- `GET /api/v1/homeworks/{id}` returns HomeworkDTO or 404.
- Includes `submission_count` (number of submissions).

### HW-1.4: Update Homework
Update homework fields (title, description, due_date, max_score). Only Teacher can update their own homeworks, or any homework if they have admin scope.

**Acceptance:**
- `PATCH /api/v1/homeworks/{id}` with partial fields returns updated HomeworkDTO.
- Cannot update if status is `closed` or `archived`.

### HW-1.5: Delete Homework
Soft-archive a homework (sets status = `archived`). Does not delete submissions or grades — data preserved.

**Acceptance:**
- `DELETE /api/v1/homeworks/{id}` returns 204.
- Homework status → `archived`.

### HW-1.6: Close Homework
Teacher closes homework — no more submissions accepted. Existing submissions can still be graded.

**Acceptance:**
- `POST /api/v1/homeworks/{id}/close` returns updated HomeworkDTO with status = `closed`.
- Subsequent `POST /submissions` for this homework → 400 "Homework is closed".
- Can be reopened via `PATCH /homeworks/{id}` with `status: "active"`.
- Audit event emitted.

---

## HW-2: Submission

### HW-2.1: Submit Homework
A Student submits their work against a homework assignment. Text content only in Phase 1.

**Acceptance:**
- `POST /api/v1/submissions` with `{ homework_id, content }` returns 201 with SubmissionDTO.
- Validates: homework exists and status is `active`.
- Validates: student has not already submitted (one submission per student per homework).
- Late detection: if `now() > homework.due_date` → status = `late`. Else → status = `submitted`.
- `submitted_at` = current timestamp.
- Audit event emitted.

### HW-2.2: List Submissions
List submissions with optional filters. Teacher sees all submissions for a homework. Student sees only their own.

**Acceptance:**
- `GET /api/v1/submissions` supports `?homework_id=`, `?student_id=`, `?status=`.
- Student ownership: if role is Student and `student_id != ctx.user_id` → 403.
- Returns SubmissionDTO list with student name (joined from app_user).

### HW-2.3: Get Submission
Get a single submission by ID. Student can only access their own.

**Acceptance:**
- `GET /api/v1/submissions/{id}` returns SubmissionDTO or 404.
- Student ownership enforced: if submission.student_id != ctx.user_id → 403 (unless Teacher/Admin).

---

## HW-3: Grading

### HW-3.1: Grade a Submission
Teacher grades a student's submission with score and feedback. Auto-updates submission status.

**Acceptance:**
- `POST /api/v1/submissions/{id}/grade` with `{ score, feedback? }` returns 201 with GradeDTO.
- Validates: submission exists.
- Auto-updates Submission.status → `graded`.
- `max_score` inherited from Homework.max_score.
- `graded_by` set to `ctx.user_id`.
- All in one transaction.
- Audit event emitted.

### HW-3.2: List Grades
List grades with optional filters.

**Acceptance:**
- `GET /api/v1/grades` supports `?submission_id=`, `?homework_id=`, `?student_id=`.
- Student ownership: can only see own grades.

### HW-3.3: Update Grade
Teacher updates a previously assigned grade (corrects a mistake).

**Acceptance:**
- `PATCH /api/v1/grades/{id}` with `{ score, feedback? }` returns updated GradeDTO.
- Audit event emitted (`grade_updated`).

---

## HW-4: Authorization

### HW-4.1: All endpoints are protected
Every homework endpoint has `Depends(require_permission(resource, action))`.

**Acceptance:**
- Without required permission → 403.
- Platform owner bypasses all checks.

### HW-4.2: Role-based access — 10 permissions

| Permission | Admin | Principal | HOD | Teacher | Student |
|---|---|---|---|---|---|
| `homework.read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `homework.create` | | | | ✅ | |
| `homework.update` | | | | ✅ | |
| `homework.delete` | | | | ✅ | |
| `homework.close` | | | | ✅ | |
| `submission.read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `submission.create` | | | | | ✅ |
| `grade.read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `grade.create` | | | | ✅ | |
| `grade.update` | | | | ✅ | |

**Acceptance:**
- Teacher can create homework; Student cannot → 403.
- Student can submit; Teacher cannot submit → 403.
- HOD/Principal/Admin are read-only (oversight).

### HW-4.3: Ownership enforcement
Students can only access their own submissions and grades.

**Acceptance:**
- If role is Student and `student_id != ctx.user_id` → 403.
- Teacher/HOD/Principal/Admin bypass ownership.

---

## HW-5: Homework Lifecycle

### HW-5.1: Status transitions

```
active ──close──→ closed ──delete──→ archived
  │                                    ↑
  └───────────delete───────────────────┘
```

- `active`: open for submissions (initial state).
- `closed`: no new submissions accepted; existing submissions can be graded.
- `archived`: hidden from default views; data preserved (soft-delete).

**Acceptance:**
- `POST /homeworks/{id}/close` → active → closed.
- `DELETE /homeworks/{id}` → active/closed → archived.
- Closed homework rejects `POST /submissions` with 400.
- Archived homeworks are excluded from default `GET /homeworks` (unless `?status=archived`).
- Closed homework can be reopened via `PATCH` with `status: "active"`.

---

## HW-6: Audit

### HW-6.1: Audit events — 6 event types

| Event | When | Payload |
|---|---|---|
| `homework_created` | POST /homeworks | `{ homework_id, title, grade_level, subject, due_date }` |
| `homework_updated` | PATCH /homeworks | `{ homework_id, changes }` |
| `homework_closed` | POST /homeworks/{id}/close | `{ homework_id }` |
| `submission_created` | POST /submissions | `{ submission_id, homework_id, student_id, status }` |
| `grade_created` | POST /submissions/{id}/grade | `{ grade_id, submission_id, score, max_score }` |
| `grade_updated` | PATCH /grades/{id} | `{ grade_id, score }` |

**Acceptance:**
- Events emitted via `AuditEmitter` after successful commit.
- Includes `client_id`, `institution_id`, `actor` in every event.

---

## HW-7: Data Isolation

### HW-7.1: RLS policies
All 3 tables have RLS enforced (same pattern as C-01/C-02/C-03/Fees).

**Acceptance:**
- `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY`.
- SELECT/INSERT/UPDATE: `is_platform_owner() OR client_id = current_client_id()`.
- DELETE: platform owner only.

### HW-7.2: Repository layer
All repositories inherit `TenantAwareRepositoryBase`. `client_id` is auto-injected.
