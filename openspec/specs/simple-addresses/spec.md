## ADDED Requirements

### Requirement: Structured address records
Feature: Simple Addresses
Rule: Addresses are stored as structured records linked to entities with type labels.

#### Scenario: Add address to a student
- **GIVEN** a student
- **WHEN** a home address is added
- **THEN** the address is saved and linked to the student

#### Scenario: Multiple addresses per entity
- **GIVEN** a student with a home address
- **WHEN** a billing address is added
- **THEN** both addresses exist with distinct type labels
