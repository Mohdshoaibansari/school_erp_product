# ADR Review — Refactor C-05 Academic Structure

> **Change:** refactor-c05-academic-structure
> **Date:** 2026-09-02

---

## ADR Review Summary

### Existing ADRs Reviewed

- `docs/architecture/adr-c05-academic-structure-implementation.md` — Current C-05 ADR (D1-D24)

### Supersession Analysis

The existing ADR (`adr-c05-academic-structure-implementation.md`) contains decisions that are **superseded** by the enhanced PRD and grill session:

| Old Decision | Status | Reason |
|---|---|---|
| D2: Separate Entities for Class and Section | Superseded | Class/Section are now permanent masters |
| D4: Room and Building in C-05 | Superseded | Removed from C-05 scope |
| D5: C-05 and OrgUnit Are Independent Trees | Superseded | GradeLevel now has org_unit_id FK |
| D8: Student Enrolled in Section | Superseded | Deferred to Student module |
| D9: Subject Assigned to Section | Superseded | Subject now belongs to CurriculumVersion |
| D10: Homeroom Teacher on Section | Superseded | Deferred to Teacher module |
| D11: Separate TeacherAssignment Entity | Superseded | Deferred to Teacher module |
| D12: Separate StudentEnrollment Entity | Superseded | Deferred to Student module |
| D13: SubjectGroup with Many-to-Many Link | Superseded | Replaced by Curriculum/CurriculumVersion |
| D15: Everything Is Year-Specific | Superseded | Permanent masters introduced |
| D16: Clone from Previous Year | Superseded | Not needed with permanent masters |
| D17: Homework References Section and Subject | Superseded | Deferred to Homework module rebuild |
| D19: Template Excludes Room and Building | Superseded | Templates removed entirely |
| D22: Clone Skips Archived/Deleted Entities | Superseded | Cloning removed |
| D24: Homework Allowed in Planning Year | Superseded | Deferred to Homework module rebuild |

### New Repository-Level ADRs

No new repository-level ADRs are created. The decisions are captured in:
- `docs/prd/C-05-Academic-Structure-enhanced.md` (business baseline)
- `docs/prd/c-05-impact-classification.md` (implementation decisions)
- This change's `design.md` (technical decisions)

### Rationale

The enhanced PRD is the consolidated business baseline. The grill session resolved all implementation questions. The existing ADR should be updated to reflect the new model, but this is a documentation task, not an architectural decision.

---

## In-Force ADRs

- `docs/architecture/adr-c01-tenant-institution-implementation.md` — C-01 (OrgUnit reference)
- `docs/architecture/adr-c02-identity-user-management-implementation.md` — C-02 (user references)
- `docs/architecture/adr-c02-identity-person-model-revamp.md` — Person model (deferred)

---

## Decision

No major durable architectural decisions are introduced beyond what's captured in the PRD and impact classification. The refactoring aligns implementation with the existing target model.
