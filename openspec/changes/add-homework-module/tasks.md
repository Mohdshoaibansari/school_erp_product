# Implementation Tasks — Homework Module

> **Traceability:** Each task traces to PRD AC-IDs and grill-me decision IDs (D1–D16). Pattern: same as Fees module tasks.

---

## 1. Module structure & manifest (D8, D15)

- [x] 1.1 Create `backend/business/homework/` directory with `__init__.py`, `manifest.py`, `models/`, `repos/`, `services/`, `routes/`, `dependencies.py`. — evidence: directory structure exists.
- [x] 1.2 Implement `HomeworkManifest` (subclass of `ManifestBase`) with `register_routes`, `register_casbin_policies` (empty), `on_startup`, `on_shutdown`, `register_cli`. Create `manifest` singleton. — evidence: `manifest.py` importable.
- [x] 1.3 Register homework manifest in `tests/conftest.py`: `create_app([..., homework_manifest])`. — evidence: app boots with homework manifest.

## 2. Database schema — migration `006_homework_module.py` (D2, D4, D5, D10, D13)

- [x] 2.1 Create `homework` table with RLS (standard pattern). — evidence: migration creates table; `test_homework_has_rls` passes.
- [x] 2.2 Create `submission` table with RLS. — evidence: migration creates table.
- [x] 2.3 Create `grade` table with RLS. — evidence: migration creates table.
- [x] 2.4 Insert 10 homework permission rows into C-04's `permission` table (ON CONFLICT DO NOTHING). — evidence: 10 new permissions exist.
- [x] 2.5 Insert ~15 role-permission rows into C-04's `role_permission` table. — evidence: role mappings exist.

## 3. ORM models (D2, D4, D5)

- [x] 3.1 Implement `Homework` model using shared `kernel.db.Base`. — evidence: model importable.
- [x] 3.2 Implement `Submission` model. — evidence: model importable.
- [x] 3.3 Implement `Grade` model. — evidence: model importable.

## 4. DTOs

- [x] 4.1 Implement Homework DTOs (create, update, response with submission_count). — evidence: DTOs importable.
- [x] 4.2 Implement Submission DTOs (create with content, response with student_name). — evidence: DTOs importable.
- [x] 4.3 Implement Grade DTOs (create with score/feedback, update, response). — evidence: DTOs importable.

## 5. Repositories (D3, D4, D5)

- [x] 5.1 Implement `HomeworkRepository` (TenantAwareRepositoryBase) — create, list (with grade_level/subject/status filters), get, update, close, archive. — evidence: repo methods exist.
- [x] 5.2 Implement `SubmissionRepository` — create, list (with homework_id/student_id/status filters), get. — evidence: repo methods exist.
- [x] 5.3 Implement `GradeRepository` — create, list (with submission_id/homework_id/student_id), get, update. — evidence: repo methods exist.

## 6. Service layer (D3, D6, D9, D12, D16)

- [x] 6.1 Implement `HomeworkService` with injected repos, session_factory, audit_emitter. — evidence: service class exists.
- [x] 6.2 Implement homework CRUD methods (create, list, get, update, delete → archive). — evidence: CRUD methods exist.
- [x] 6.3 Implement `close_homework` — sets status = 'closed'. — evidence: close method exists.
- [x] 6.4 Implement `submit` — creates submission, late detection (compare now() vs homework.due_date). — evidence: submit method with late logic.
- [x] 6.5 Implement `grade_submission` — creates grade, auto-updates submission.status = 'graded'. All in one transaction. — evidence: grade method with status update.
- [x] 6.6 Implement `update_grade` — updates score/feedback. — evidence: update method exists.
- [x] 6.7 Implement ownership enforcement — Student can only access own submissions/grades. — evidence: `_enforce_ownership` method exists.

## 7. Routes (D14)

- [x] 7.1 Implement `routes/homeworks.py` (6 endpoints: create, list, get, update, delete, close). All with `Depends(require_permission(...))`. — evidence: routes mount and return correct responses.
- [x] 7.2 Implement `routes/submissions.py` (3 endpoints: submit, list, get). Student ownership enforced. — evidence: routes with ownership.
- [x] 7.3 Implement `routes/grades.py` (3 endpoints: grade, list, update). — evidence: routes mount.

## 8. Dependencies

- [x] 8.1 Implement `get_homework_service()` dependency (singleton pattern, same as Fees). — evidence: dependency returns service.

## 9. Audit (D11)

- [x] 9.1 Emit `homework_created` on POST /homeworks. — evidence: audit event emitted.
- [x] 9.2 Emit `homework_updated` on PATCH /homeworks. — evidence: audit event emitted.
- [x] 9.3 Emit `homework_closed` on POST /homeworks/{id}/close. — evidence: audit event emitted.
- [x] 9.4 Emit `submission_created` on POST /submissions. — evidence: audit event emitted.
- [x] 9.5 Emit `grade_created` on POST /submissions/{id}/grade. — evidence: audit event emitted.
- [x] 9.6 Emit `grade_updated` on PATCH /grades/{id}. — evidence: audit event emitted.

## 10. Integration tests (AC-1 through AC-8)

- [x] 10.1 Test homework CRUD (AC-1): create, list filters, get, update, delete (archive). — evidence: `test_homework_crud` passes.
- [x] 10.2 Test submission + late detection (AC-2): submit homework, late status when past due_date. — evidence: `test_submission_late_detection` passes.
- [x] 10.3 Test grading + status update (AC-3): grade submission, auto-update to 'graded'. — evidence: `test_grade_updates_submission_status` passes.
- [x] 10.4 Test lifecycle (AC-4): close homework rejects submissions, reopen, archive. — evidence: `test_homework_lifecycle` passes.
- [x] 10.5 Test student ownership (AC-5): student sees own, blocked from others. — evidence: `test_student_ownership` passes.
- [x] 10.6 Test authorization (AC-6): Teacher can create homework; Student cannot. Real Casbin enforcer. — evidence: `test_authz_teacher_create`, `test_authz_student_blocked` pass.
- [x] 10.7 Test audit (AC-7): 6 event types emitted. — evidence: `test_audit_events` passes.

## 11. Regression

- [x] 11.1 All existing tests pass (~301 baseline). — evidence: `uv run python -m pytest tests/ -q` passes.
- [x] 11.2 Import-linter: 2 kept, 0 broken. — evidence: `uv run lint-imports` clean.
