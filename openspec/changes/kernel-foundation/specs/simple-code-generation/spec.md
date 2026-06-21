## ADDED Requirements

### Requirement: Auto-incrementing identifiers
Feature: Simple Code Generation
Rule: Identifiers are generated atomically per scope with configurable formats.

#### Scenario: Generate student ID
- **GIVEN** an institution with student ID format STU-{YEAR}-{SEQ:5}
- **WHEN** a student is enrolled
- **THEN** an identifier is generated as STU-2026-00001
- **AND** the sequence counter increments atomically

#### Scenario: Per-year sequence reset
- **GIVEN** an institution that generated 150 student IDs in 2025
- **WHEN** the first student enrolls in 2026
- **THEN** the ID is STU-2026-00001 (sequence resets per year)
- **AND** no duplicate IDs exist
