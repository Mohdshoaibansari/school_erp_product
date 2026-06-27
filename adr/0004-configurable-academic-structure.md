# ADR-0004: Configurable academic structure

## Status

Accepted

## Context

Indian schools use diverse naming and hierarchy conventions: State Board uses "Standard + Division", CBSE uses "Class + Section" with optional "Stream" at 11th/12th, small rural schools skip sections entirely. Hardcoding any one pattern locks the product to a subset of schools. The academic structure is the spine of the data model — every module (attendance, fees, exams, timetable) depends on it.

## Decision

Make the academic hierarchy configurable per school via two tables:

- `level_definitions`: A school defines which levels exist (Class, Section, Stream), their display order, and whether each is required.
- `level_instances`: Actual values form a tree via self-referencing `parent_id`. Students are assigned to the deepest (leaf) level instance.

A CBSE school with senior secondary would define: Class (level 1, required) → Stream (level 2, optional) → Section (level 3, optional). A rural primary school would define only: Class (level 1, required).

## Consequences

- **Easier**: One product serves all Indian school boards. Schools self-configure during onboarding without code changes.
- **Harder**: Queries require traversing the level instance tree to find a student's full path (Class → Stream → Section). UI must dynamically render the hierarchy based on configuration. Index `parent_id` and `school_id` for acceptable performance.
- **Constraint**: All modules consuming academic data must go through kernel's `AcademicService`, which abstracts the tree traversal. Modules never query `level_instances` directly.
