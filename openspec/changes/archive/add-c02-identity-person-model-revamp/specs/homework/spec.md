# Delta Spec — Homework (Person-Model Revamp)

> **Change:** `add-c02-identity-person-model-revamp`
> **Domain:** homework
> **Delta type:** MODIFIED + Cross-cutting
> **Base spec:** `openspec/specs/homework/spec.md` (frontend-only archived spec)
> **Source ADR:** `docs/architecture/adr-c02-identity-person-model-revamp.md` (D3a)
> **Source PRD:** `docs/prd/c02-identity-person-model-revamp.md` (AC-16)

---

## MODIFIED Requirements

### REQ-FE-HW-02: Submissions and Grading (Modified — student key shift)

Submissions are per-student. The student key SHALL shift from `app_user`-keyed to `student`-keyed (via `person`). Frontend behavior is unchanged (still lists per-student submissions), but the underlying student identity is `student.id` (linked to `person`), not `app_user.id`. Per AC-16.

> **Note:** The `student` table lands in the next capability (domain split). This revamp delivers `person` as the anchor; the actual `student`-keyed submission executes after the domain split.

#### Scenario: Submissions keyed by student entity (after domain split)
- **WHEN** an Institution Admin opens a homework's submissions
- **THEN** submissions SHALL be listed per `student.id` (linked to `person`)
- **AND** SHALL NOT use `app_user.id` as the submission student identity

---

## Cross-Cutting Notes (backend, not in archived spec)

> **Gap:** There is no archived backend-homework OpenSpec spec. The `submission.student_id` FK repoint is an implementation/migration concern, not spec'd behavior. The design phase should decide whether a backend-homework delta spec is needed or whether this is captured purely as a migration/implementation concern.

- **`submission.student_id` FK** repoints `app_user.id` → `student.id` (via `person`). Setup in this revamp's migration; execution in the next capability.
