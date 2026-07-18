# Homework Module — Specification (ADDED)

> **Domain:** `homework` | **Tier:** Business | **Depends:** C-01, C-02, C-04, C-11

## HW-1: Homework Management
- Teacher creates homework (title, description, subject, grade_level, section, due_date, max_score). Status = 'active'.
- List with `?grade_level=`, `?subject=`, `?status=` filters.
- UPDATE allowed (Teacher). DELETE = soft-archive (status = 'archived').
- POST /close → status = 'closed', blocks new submissions.

## HW-2: Submission
- Student submits (content TEXT). Late check: submitted_at > due_date → status = 'late'.
- List with `?homework_id=`, `?student_id=` filters. Student ownership enforced.
- Student: only own submissions. Teacher: all visible.

## HW-3: Grading
- Teacher creates grade (score, feedback) on a submission.
- Auto-updates submission.status → 'graded'.
- UPDATE grade allowed (Teacher). Audit on create + update.

## HW-4: Authorization
- All endpoints have `require_permission(resource, action)`.
- Teacher: homework.*, submission.read, grade.*
- Student: homework.read, submission.read (own), submission.create (own), grade.read (own)
- HOD/Principal/Admin: read-only oversight.

## HW-5: Audit
- 6 event types: homework_created/updated/closed, submission_created, grade_created/updated.

## HW-6: Data Isolation
- RLS on all 3 tables. Repos inherit TenantAwareRepositoryBase.
