# ADR-0005: Attribute-based authorization with RBAC foundation

## Status

Accepted

## Context

Role-based access control (RBAC) alone is insufficient for school operations. A "Teacher" role grants access to the attendance module, but within that module, a teacher must see only their assigned section — not every section in the school. Similarly, a subject teacher entering grades must see only their assigned subject and classes.

Designing this as a separate "scope" field on every query is fragile. The enforcement must be centralized so modules cannot accidentally widen their scope.

## Decision

Authorization has two layers:

1. **RBAC**: Roles (Super Admin, School Admin, Principal, Teacher, Accountant) gate module-level access. Defined in a role-permissions configuration.
2. **Attribute-based scoping**: Two junction tables in the database:
   - `class_teachers` (teacher_id, level_instance_id): Defines attendance duty scope. A teacher marked as class teacher of Section 5A sees only 5A students in attendance.
   - `subject_teachers` (teacher_id, subject_id, level_instance_id): Defines teaching duty scope. A teacher assigned Mathematics to Sections 5A, 5B, 6A sees only those sections for Mathematics grades.

Kernel's `AuthorizationService` resolves scope from these tables. Modules call kernel with intent ("get my attendance roster") and kernel applies the appropriate scope filter from `class_teachers` or `subject_teachers`.

## Consequences

- **Easier**: Modules never decide scope — they cannot leak data. Adding a new teacher assignment automatically adjusts their view. Scope rules are database-backed and auditable.
- **Harder**: Teachers who teach multiple subjects or are class teacher for multiple sections need both `class_teachers` and `subject_teachers` entries. Admin must manage both assignment types. Future: parent scope (linking parent to student) follows the same pattern via a `parent_students` junction table.
