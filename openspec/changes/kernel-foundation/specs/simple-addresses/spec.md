## ADDED Requirements

### Requirement: Structured address records
Feature: Simple Addresses
Rule: Addresses are stored as structured records linked to entities.

#### Scenario: Add address to a student
- **GIVEN** a student record
- **WHEN** a home address is added with line1, city, state, postalCode, country
- **THEN** the address is saved
- **AND** is linked to the student as their primary home address

#### Scenario: Multiple addresses per entity
- **GIVEN** a student with a home address
- **WHEN** a billing address is added
- **THEN** both addresses are associated with the student
- **AND** each has a distinct type label
