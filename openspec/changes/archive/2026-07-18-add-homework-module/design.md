# Homework Module — Technical Design

## 1. Module Structure (matching Fees pattern)

```
backend/business/homework/
├── __init__.py
├── manifest.py              # ModuleManifest (A5)
├── models/
│   ├── __init__.py
│   └── homework_models.py   # Homework, Submission, Grade
├── repos/
│   ├── __init__.py
│   └── homework_repos.py    # 3 repos inheriting TenantAwareRepositoryBase
├── services/
│   ├── __init__.py
│   ├── service.py           # HomeworkService
│   └── dtos.py
├── routes/
│   ├── __init__.py
│   ├── homeworks.py         # 6 endpoints
│   ├── submissions.py       # 3 endpoints
│   └── grades.py            # 3 endpoints
└── dependencies.py          # get_homework_service()
```

## 2. Database Schema (Migration 006)

3 tables with RLS (same pattern as Fees):
- `homework`: id, client_id, institution_id, title, description, subject, grade_level, section, due_date, max_score, status, assigned_by, created_at
- `submission`: id, client_id, institution_id, homework_id, student_id, content, status (submitted/late/graded), submitted_at, created_at
- `grade`: id, client_id, institution_id, submission_id, score, max_score, feedback, graded_by, graded_at, created_at

C-04 extension: 10 permission rows + ~15 role_permission rows (ON CONFLICT DO NOTHING).

## 3. Key Service Methods

### HomeworkService
- `create_homework(ctx, dto)` → HomeworkDTO + audit(homework_created)
- `list_homeworks(ctx, grade_level?, subject?, status?)` → list[HomeworkDTO]
- `get_homework(ctx, id)` → HomeworkDTO
- `update_homework(ctx, id, dto)` → HomeworkDTO + audit(homework_updated)
- `delete_homework(ctx, id)` → None (status = archived)
- `close_homework(ctx, id)` → HomeworkDTO + audit(homework_closed)

### Submission
- `submit(ctx, dto)` → SubmissionDTO (late detection, audit)
- `list_submissions(ctx, homework_id?, student_id?, status?)` → list[SubmissionDTO] (ownership enforced)
- `get_submission(ctx, id)` → SubmissionDTO (ownership enforced)

### Grading
- `grade_submission(ctx, submission_id, dto)` → GradeDTO (auto-update submission.status, audit)
- `list_grades(ctx, submission_id?, homework_id?, student_id?)` → list[GradeDTO] (ownership)
- `update_grade(ctx, grade_id, dto)` → GradeDTO + audit(grade_updated)

### Late detection
```python
homework = repo.get_homework(session, homework_id)
if datetime.now() > homework.due_date:
    status = "late"
else:
    status = "submitted"
```

### Ownership enforcement
```python
STUDENT_ROLES = {"Student", "Parent"}
if requested_student_id and any(r in STUDENT_ROLES for r in ctx.roles):
    if str(requested_student_id) != str(ctx.user_id):
        raise ValueError("You can only access your own records")
```

## 4. Authorization
All endpoints use `Depends(require_permission(resource, action))`. 10 permissions registered via migration into C-04 tables.

## 5. Testing
Same pattern as Fees:
- AlwaysAllowEnforcer for existing test compatibility
- Real Casbin enforcer for authorization tests
- Ownership tests, lifecycle tests, audit tests
