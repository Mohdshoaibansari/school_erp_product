# Spec Delta — Identity & User Management (MODIFIED)

> **Change:** add-c05-academic-structure
> **Domain:** identity-user-management
> **Impact:** MODIFIED (new FK references from C-05)
> **Source:** `docs/architecture/adr-c05-academic-structure-implementation.md` (D10, D11, D12)

---

## ADDED Requirements

### REQ-USER-AC-01: Teacher Assignment Reference

C-05 `TeacherAssignment` references `app_user.id` for teacher assignment.

**Fields affected:**
- `teacher_assignment.teacher_id` → FK to `app_user.id`
- `section.homeroom_teacher_id` → FK to `app_user.id`

**Rules:**
- Teacher must exist in `app_user` table
- Teacher must have "Teacher" role (validated in service layer)
- No schema changes to C-02 tables — FK is on C-05 side

---

### REQ-USER-AC-02: Student Enrollment Reference

C-05 `StudentEnrollment` references `app_user.id` for student enrollment.

**Fields affected:**
- `student_enrollment.student_id` → FK to `app_user.id`

**Rules:**
- Student must exist in `app_user` table
- Student must have "Student" role (validated in service layer)
- No schema changes to C-02 tables — FK is on C-05 side
