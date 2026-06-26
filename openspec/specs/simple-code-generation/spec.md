## ADDED Requirements

### Requirement: Auto-incrementing identifiers
Feature: Simple Code Generation
Rule: Identifiers are generated atomically per scope with configurable formats.

#### Scenario: Generate student ID
- **GIVEN** a configured format "STU-{YEAR}-{SEQ:5}"
- **WHEN** generating a student ID
- **THEN** the format is applied and the sequence increments atomically

#### Scenario: Per-year sequence reset
- **GIVEN** a sequence counter for 2026
- **WHEN** the year changes to 2027
- **THEN** the sequence resets to 1 and no duplicates are generated
