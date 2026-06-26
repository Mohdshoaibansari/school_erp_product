## ADDED Requirements

### Requirement: File upload and download
Feature: Simple Documents
Rule: All file storage flows through this service; no module stores files independently.

#### Scenario: Upload a document
- **GIVEN** a file with metadata (type, entity reference)
- **WHEN** the document is uploaded
- **THEN** the file is stored and a document record is created linking the file to the entity

#### Scenario: Download a document
- **GIVEN** an existing document
- **WHEN** an authorized user requests download
- **THEN** the file is returned
