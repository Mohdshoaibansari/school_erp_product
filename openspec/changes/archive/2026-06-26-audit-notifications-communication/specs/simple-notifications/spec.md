## ADDED Requirements

### Requirement: Email notification delivery
Feature: Simple Notifications
Rule: All email notifications flow through this service; no module sends email directly.

#### Scenario: Send a notification email
- **GIVEN** a notification template and recipient
- **WHEN** the notification is sent
- **THEN** the template is rendered, email is sent, and delivery status is recorded

#### Scenario: Notification delivery failure
- **GIVEN** an invalid recipient
- **WHEN** the notification fails
- **THEN** the failure is recorded and the calling module is not crashed
