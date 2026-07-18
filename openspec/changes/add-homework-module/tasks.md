# Tasks — Homework Module (~35 tasks)

## 1. Module Structure
- [ ] 1.1 Create `backend/business/homework/` directory with sub-packages.
- [ ] 1.2 Implement `HomeworkManifest` (A5).
- [ ] 1.3 Register in `tests/conftest.py`.

## 2. DB Schema (Migration 006)
- [ ] 2.1 Create `homework` table with RLS.
- [ ] 2.2 Create `submission` table with RLS.
- [ ] 2.3 Create `grade` table with RLS.
- [ ] 2.4 Insert 10 permission rows into C-04 tables.
- [ ] 2.5 Insert ~15 role_permission rows.

## 3. ORM Models
- [ ] 3.1 Homework model.
- [ ] 3.2 Submission model.
- [ ] 3.3 Grade model.

## 4. DTOs
- [ ] 4.1 Homework DTOs (create, update, response).
- [ ] 4.2 Submission DTOs.
- [ ] 4.3 Grade DTOs.

## 5. Repositories
- [ ] 5.1 HomeworkRepository (TenantAwareRepositoryBase).
- [ ] 5.2 SubmissionRepository.
- [ ] 5.3 GradeRepository.

## 6. Service Layer
- [ ] 6.1 HomeworkService class.
- [ ] 6.2 Homework CRUD methods.
- [ ] 6.3 close_homework method.
- [ ] 6.4 submit_homework (late detection).
- [ ] 6.5 grade_submission (auto-update submission.status).
- [ ] 6.6 update_grade method.
- [ ] 6.7 Ownership enforcement.

## 7. Routes
- [ ] 7.1 `routes/homeworks.py` (6 endpoints, all with require_permission).
- [ ] 7.2 `routes/submissions.py` (3 endpoints, student ownership).
- [ ] 7.3 `routes/grades.py` (3 endpoints).

## 8. Dependencies
- [ ] 8.1 `get_homework_service()` dependency.

## 9. Audit
- [ ] 9.1 Emit homework_created/updated/closed.
- [ ] 9.2 Emit submission_created.
- [ ] 9.3 Emit grade_created/updated.

## 10. Integration Tests
- [ ] 10.1 Test homework CRUD (AC-1).
- [ ] 10.2 Test submission + late detection (AC-2).
- [ ] 10.3 Test grading + status update (AC-3).
- [ ] 10.4 Test lifecycle (AC-4).
- [ ] 10.5 Test student ownership (AC-5).
- [ ] 10.6 Test authorization (AC-6).
- [ ] 10.7 Test audit (AC-7).

## 11. Regression
- [ ] 11.1 All existing tests pass.
- [ ] 11.2 Import-linter: 2 kept, 0 broken.
