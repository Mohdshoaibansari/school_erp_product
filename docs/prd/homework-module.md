# Homework Module — Product Requirements Document

> **Status:** Draft  
> **Version:** 1.0  
> **Date:** 2026-07-18  
> **Author:** Platform Team  
> **Purpose:** Define the Homework business module — second business module validating platform integration patterns alongside Fees.

---

## 1. Problem

Teachers need to create homework assignments, distribute them to students, collect submissions, and grade them. Currently this is done via paper, email, or standalone tools with no integration to the student identity system, no multi-tenant isolation, and no audit trail. This module:

- Consumes C-01 (tenant/institution isolation)
- Consumes C-02 (teacher/student identity)
- Consumes C-03 (authentication)
- Consumes C-04 (role-based authorization)
- Emits C-11 (audit events)
- Validates platform integration for a second business domain

---

## 2. Goals & Non-Goals

### Goals
- G1: Teachers can create homework with title, description, subject, grade_level, section, due_date.
- G2: Students can view assigned homework and submit their work.
- G3: Teachers can view submissions and grade them with score + feedback.
- G4: Homework has a lifecycle: active → closed → archived.
- G5: Late submissions are marked automatically.
- G6: Students can only see their own submissions (ownership enforced).
- G7: All endpoints are protected by C-04 role-based authorization.
- G8: Every significant action generates an audit event.

### Non-Goals
- C-05 Academic Structure integration (free-text grade/class/subject)
- C-06 Relationship Management (parent-child homework visibility)
- C-09 Notifications (homework alerts, due date reminders)
- C-10 Communication (teacher-student messaging about homework)
- C-14 Document Management (file uploads)
- Bulk grading, rubric-based grading
- Resubmission / iterative feedback
- Draft homework state

---

## 3. Users / Personas

| Persona | Role | Needs |
|---|---|---|
| Teacher | Teacher role | Create/edit/close homework, view submissions, grade work |
| HOD | HOD role | View homework and grades (oversight) |
| Principal | Principal role | View homework and grades (oversight) |
| Student | Student role | View assigned homework, submit work, view own grades |
| Admin | Admin role | Oversight of all homework data |

---

## 4. User Journeys

### J1: Teacher creates homework
1. Teacher navigates to Homework, clicks "New Homework."
2. Fills in title, description, subject ("Mathematics"), grade_level ("Grade 5"), section ("A"), due_date, max_score.
3. Homework is created with status `active`.

### J2: Student submits homework
1. Student sees active homeworks for their grade/section.
2. Opens a homework, writes answer in the text field.
3. Clicks "Submit." Submission is created with status `submitted` (or `late` if past due_date).

### J3: Teacher grades a submission
1. Teacher opens a homework, sees list of all submissions.
2. Opens a submission, enters score (e.g., 85/100) and feedback.
3. Clicks "Grade." Grade is created, submission status → `graded`.

### J4: Teacher closes homework
1. Teacher clicks "Close Homework" → no more submissions accepted.
2. Homework status → `closed`.

### J5: Student views their grades
1. Student navigates to "My Grades," sees all their graded submissions.

### J6: Teacher updates a grade
1. Teacher realizes a grade is wrong, edits the score.
2. PATCH /grades/{id} updates score/feedback. Audit event emitted.

---

## 5. Entities

### Homework
| Field | Type |
|---|---|
| id | UUID PK |
| client_id | UUID FK → client |
| institution_id | UUID FK → institution |
| title | TEXT NOT NULL |
| description | TEXT |
| subject | TEXT (Phase 2 → C-05 FK) |
| grade_level | TEXT (Phase 2 → C-05 FK) |
| section | TEXT (Phase 2 → C-05 FK) |
| due_date | DATE NOT NULL |
| max_score | INT |
| status | TEXT DEFAULT 'active' |
| assigned_by | UUID FK → app_user |
| created_at | TIMESTAMPTZ |

### Submission
| Field | Type |
|---|---|
| id | UUID PK |
| client_id | UUID FK → client |
| institution_id | UUID FK → institution |
| homework_id | UUID FK → homework |
| student_id | UUID FK → app_user |
| content | TEXT |
| status | TEXT DEFAULT 'submitted' |
| submitted_at | TIMESTAMPTZ |
| created_at | TIMESTAMPTZ |

### Grade
| Field | Type |
|---|---|
| id | UUID PK |
| client_id | UUID FK → client |
| institution_id | UUID FK → institution |
| submission_id | UUID FK → submission |
| score | INT NOT NULL |
| max_score | INT |
| feedback | TEXT |
| graded_by | UUID FK → app_user |
| graded_at | TIMESTAMPTZ |
| created_at | TIMESTAMPTZ |

---

## 6. API Endpoints (~12)

### Homeworks
| Method | Path | Permission |
|---|---|---|
| GET | `/api/v1/homeworks` | `homework.read` |
| POST | `/api/v1/homeworks` | `homework.create` |
| GET | `/api/v1/homeworks/{id}` | `homework.read` |
| PATCH | `/api/v1/homeworks/{id}` | `homework.update` |
| DELETE | `/api/v1/homeworks/{id}` | `homework.delete` |
| POST | `/api/v1/homeworks/{id}/close` | `homework.close` |

### Submissions
| Method | Path | Permission |
|---|---|---|
| GET | `/api/v1/submissions` | `submission.read` |
| POST | `/api/v1/submissions` | `submission.create` |
| GET | `/api/v1/submissions/{id}` | `submission.read` |

### Grades
| Method | Path | Permission |
|---|---|---|
| GET | `/api/v1/grades` | `grade.read` |
| POST | `/api/v1/submissions/{id}/grade` | `grade.create` |
| PATCH | `/api/v1/grades/{id}` | `grade.update` |

---

## 7. C-04 Authorization (~10 permissions)

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

---

## 8. C-11 Audit (6 events)

| Event | When |
|---|---|
| `homework_created` | POST /homeworks |
| `homework_updated` | PATCH /homeworks |
| `homework_closed` | POST /homeworks/{id}/close |
| `submission_created` | POST /submissions |
| `grade_created` | POST /submissions/{id}/grade |
| `grade_updated` | PATCH /grades/{id} |

---

## 9. Acceptance Criteria (AC-1 through AC-8)

### AC-1: Homework CRUD
- Teacher can create/list/get/update/delete homework.
- Student can list/get homework matching their grade_level + section.

### AC-2: Submission
- Student can submit homework (text content).
- Late detection: if submitted after due_date → status = "late".

### AC-3: Grading
- Teacher can grade a submission (score + feedback).
- Submission status auto-updates to "graded".
- Teacher can update a grade.

### AC-4: Lifecycle
- Homework transitions: active → closed (POST /close), closed → archived (DELETE).
- Closed homework rejects new submissions.

### AC-5: Student ownership
- Student sees only their own submissions and grades.
- Student cannot see another student's submissions.

### AC-6: Authorization
- Teacher can create homework; Student cannot.
- Student can submit; Teacher cannot submit (they grade).
- HOD/Principal/Admin are read-only.

### AC-7: Audit
- 6 event types emitted as defined.

### AC-8: RLS
- All 3 tables have RLS enforced.

---

## 10. Decision Log

| # | Topic | Decision |
|---|---|---|
| D1 | Entities | Homework + Submission + Grade |
| D2 | Homework schema | Minimal, C-05 ready |
| D3 | Assignment | No bridge table; grade_level + section targeting |
| D4 | Submission | Text-based, status: submitted/late/graded |
| D5-6 | Grade + flow | Separate table, auto-update submission |
| D7 | C-04 | ~10 permissions |
| D8 | Location | `backend/business/homework/` |
| D9 | Ownership | `?student_id=` filter + backend check |
| D10 | RLS | All 3 tables |
| D11 | Audit | 6 events |
| D12 | Late | Computed at creation |
| D13 | Permission reg | Migration → C-04 tables |
| D14 | Endpoints | ~12 REST |
| D15 | Manifest | Full A5 hooks |
| D16 | Lifecycle | active → closed → archived |
