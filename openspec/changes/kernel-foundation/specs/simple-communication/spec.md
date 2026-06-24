## ADDED Requirements

### Requirement: Direct messaging
Feature: Simple Communication
Rule: Teachers and parents can exchange direct messages.

#### Scenario: Teacher sends message to parent
- **GIVEN** a teacher and a parent with a student relationship
- **WHEN** the teacher sends a message to the parent
- **THEN** a conversation is created between teacher and parent
- **AND** the parent receives an in-app notification

#### Scenario: Parent replies to teacher
- **GIVEN** an existing conversation between a teacher and a parent
- **WHEN** the parent sends a reply
- **THEN** the message is added to the conversation thread
- **AND** the teacher receives an in-app notification
