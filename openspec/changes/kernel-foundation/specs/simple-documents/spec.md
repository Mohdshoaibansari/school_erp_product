## ADDED Requirements

### Requirement: File upload and download
Feature: Simple Documents
Rule: All file storage flows through this service. No module stores files independently.

#### Scenario: Upload a document
- **GIVEN** an authenticated user
- **WHEN** they upload a file with metadata (type, entity reference)
- **THEN** the file is stored
- **AND** a document record is created linking the file to the entity

#### Scenario: Download a document
- **GIVEN** a stored document
- **WHEN** an authorized user requests the document
- **THEN** the file is returned for download
