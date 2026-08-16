# Verification Report — C-05 Academic Structure Framework

> **Change:** add-c05-academic-structure
> **Verified:** 2026-08-15
> **Status:** PASS — Ready for manual testing

---

## Summary

| Dimension | Status |
|---|---|
| **Completeness** | 42/42 tasks complete, 18/18 requirements implemented |
| **Correctness** | All requirements have implementation evidence |
| **Coherence** | Follows project patterns (module structure, models, repos, routes, manifest) |

---

## Completeness

### Task Completion

| Phase | Tasks | Status |
|---|---|---|
| Models + Migration | T01-T13 | ✅ 13/13 |
| Repos | T14-T18 | ✅ 5/5 |
| Services | T19-T23 | ✅ 5/5 |
| Routes | T24-T29 | ✅ 6/6 |
| Downstream Migration | T30-T35 | ✅ 6/6 |
| Tests | T36-T42 | ✅ 7/7 |
| **Total** | **42** | **✅ 42/42** |

### Spec Coverage

| Spec File | Requirements | Implemented | Status |
|---|---|---|---|
| academic-structure/spec.md | 14 (REQ-AC-01 to REQ-AC-14) | 14 | ✅ |
| configuration-framework/spec.md | 1 (REQ-CONFIG-AC-01) | 1 | ✅ |
| authorization/spec.md | 1 (REQ-AUTHZ-AC-01) | 1 | ✅ |
| identity-user-management/spec.md | 2 (REQ-USER-AC-01, REQ-USER-AC-02) | 2 | ✅ |
| **Total** | **18** | **18** | **✅** |

---

## Correctness

### Requirement Implementation Evidence

| Requirement | Evidence | Status |
|---|---|---|
| REQ-AC-01: AcademicYear | `kernel/academic/models/academic_year.py` — class with lifecycle fields | ✅ |
| REQ-AC-02: Term | `kernel/academic/models/term.py` — child of AcademicYear | ✅ |
| REQ-AC-03: GradeLevel | `kernel/academic/models/grade_level.py` — year-specific | ✅ |
| REQ-AC-04: Class | `kernel/academic/models/class_entity.py` — FK to GradeLevel | ✅ |
| REQ-AC-05: Section | `kernel/academic/models/section.py` — homeroom_teacher_id | ✅ |
| REQ-AC-06: Subject | `kernel/academic/models/subject.py` — year-specific | ✅ |
| REQ-AC-07: SubjectGroup | `kernel/academic/models/subject_group.py` — many-to-many | ✅ |
| REQ-AC-08: SubjectGroupMember | `kernel/academic/models/subject_group.py` — bridge table | ✅ |
| REQ-AC-09: TeacherAssignment | `kernel/academic/models/teacher_assignment.py` — teacher+section+subject | ✅ |
| REQ-AC-10: StudentEnrollment | `kernel/academic/models/student_enrollment.py` — student+section | ✅ |
| REQ-AC-11: Template | `kernel/academic/services/template_service.py` — generates from config | ✅ |
| REQ-AC-12: Cloning | `kernel/academic/services/clone_service.py` — clones from previous year | ✅ |
| REQ-AC-13: Soft-close | `kernel/academic/services/lifecycle_service.py` — non-blocking close | ✅ |
| REQ-AC-14: Homework in planning | `kernel/academic/services/lifecycle_service.py` — no gate on content | ✅ |
| REQ-CONFIG-AC-01 | `migrations/versions/020_*.py` — 4 config keys seeded | ✅ |
| REQ-AUTHZ-AC-01 | `migrations/versions/020_*.py` — 10 permissions seeded | ✅ |
| REQ-USER-AC-01 | `kernel/academic/models/section.py` — homeroom_teacher_id FK | ✅ |
| REQ-USER-AC-02 | `kernel/academic/models/student_enrollment.py` — student_id FK | ✅ |

---

## Coherence

### Design Adherence

| Decision | Implementation | Status |
|---|---|---|
| D6: AcademicYear lifecycle | `lifecycle_service.py` — planning → active → closed | ✅ |
| D7: Config-driven template | `template_service.py` — reads from C-08 config | ✅ |
| D14: Term child of AcademicYear | `term.py` — academic_year_id FK | ✅ |
| D15: Year-specific entities | All entities have academic_year_id | ✅ |
| D16: Clone from previous year | `clone_service.py` — clone_from_year() | ✅ |
| D19: Template excludes Room/Building | No Room/Building in template_service | ✅ |
| D20: Non-blocking close | `lifecycle_service.py` — _close() archives enrollments | ✅ |
| D22: Clone skips archived | `clone_service.py` — filters archived_at IS NULL | ✅ |

### Code Pattern Consistency

| Pattern | Evidence | Status |
|---|---|---|
| Module structure | `kernel/academic/` — models, repos, services, routes, manifest | ✅ |
| Models extend Base | All models use `from kernel.db import Base` | ✅ |
| UUID PKs | All models use `uuid.uuid4` default | ✅ |
| client_id + institution_id | All entities (except SubjectGroupMember) have both | ✅ |
| Repos use Session injection | All repos take `db: Session` in __init__ | ✅ |
| Routes use require_permission | All routes have `_authz: None = Depends(require_permission(...))` | ✅ |
| Manifest protocol | register_routes, register_casbin_policies, on_startup, on_shutdown | ✅ |
| RLS policies | 10 tables with RLS (9 with full policies, 1 enabled only) | ✅ |
| Indexes | 14 indexes on FK columns | ✅ |

---

## Migration Verification

| Migration | Tables | Config Keys | Permissions | Indexes | Status |
|---|---|---|---|---|---|
| 020_add_c05_academic_structure | 10 | 4 | 10 | 14 | ✅ |
| 021_homework_fee_assignment_academic_fks | 0 (alter) | 0 | 0 | 4 | ✅ |

---

## Issues

### CRITICAL

None.

### WARNING

None.

### SUGGESTION

1. **SUGGESTION:** The migration 021 drops old free-text columns immediately after backfill. In production, consider a two-phase approach: add FK columns → deploy → backfill → verify → drop old columns in a separate migration.
   - File: `migrations/versions/021_homework_fee_assignment_academic_fks.py`
   - Recommendation: Split into two migrations for safer production deployment.

2. **SUGGESTION:** The `subject_group_member` table has RLS enabled but no policies (no client_id column). This means platform owners can access it but tenant users cannot.
   - File: `migrations/versions/020_add_c05_academic_structure.py`
   - Recommendation: Add RLS policies if subject groups need tenant isolation.

---

## Final Assessment

**✅ PASS — Ready for manual testing.**

- 42/42 tasks complete
- 18/18 requirements implemented
- All design decisions followed
- Code patterns consistent with project
- 2 suggestions for production hardening (non-blocking)
