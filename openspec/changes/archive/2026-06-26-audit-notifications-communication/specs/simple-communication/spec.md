## ADDED Requirements

### Requirement: Direct messaging
Feature: Simple Communication
Rule: Teachers and parents can exchange messages within conversation threads.

#### Scenario: Teacher sends message to parent
- **GIVEN** a teacher and parent linked to a student
- **WHEN** the teacher sends a message
- **THEN** a conversation is created and the parent receives an in-app notification

#### Scenario: Parent replies to teacher
- **GIVEN** an existing conversation between teacher and parent
- **WHEN** the parent replies
- **THEN** the message is added to the thread and the teacher receives an in-app notification
