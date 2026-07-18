# Add Homework Business Module

## Summary

Add the Homework business module — the second business module built on the platform foundation, following the same patterns as the Fees module. Validates that platform integration (tenant isolation, authorization, audit) works across multiple business domains.

## Motivation

- Second business module: proves the Fees module was not a one-off — the platform patterns are reusable.
- Teachers need to create homework, students need to submit, teachers need to grade.
- Validates C-04 authorization for a third set of resources (homework/submission/grade).

## Scope

### In Scope
- 3 entities: Homework, Submission, Grade
- ~12 REST endpoints
- C-04 authorization: 10 new permissions, ~15 role mappings
- C-11 audit: 6 event types
- Student ownership enforcement
- Late submission detection
- Homework lifecycle: active → closed → archived

### Out of Scope
- C-05 Academic Structure integration (free-text grade/class/subject)
- C-09 Notifications, C-10 Communication, C-14 Document Management
- Bulk grading, rubric grading, resubmission, draft state

## Impact

- **ADDED:** `homework` domain — new business module at `backend/business/homework/`
- **MODIFIED:** `authorization` domain — 10 new permission rows + ~15 role_permission rows in C-04's tables (no C-04 code changes)
- **No changes** to C-01, C-02, C-03, C-11

## References
- PRD: `docs/prd/homework-module.md`
- Impact: `docs/prd/homework-module-impact.md`
- Grill decisions: D1–D16
- Pattern reference: `openspec/changes/archive/2026-07-17-add-fees-module/`
