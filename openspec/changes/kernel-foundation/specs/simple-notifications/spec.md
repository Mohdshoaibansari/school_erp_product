## ADDED Requirements

### Requirement: Email notification delivery
Feature: Simple Notifications
Rule: Modules send email notifications through this service. No module sends email directly.

#### Scenario: Send a notification email
- **GIVEN** a notification template with variables
- **WHEN** a module requests a notification with recipient email and template data
- **THEN** the service renders the template
- **AND** sends the email via the configured email provider
- **AND** records the delivery status

#### Scenario: Notification delivery failure
- **GIVEN** an invalid recipient email
- **WHEN** a notification is sent
- **THEN** the service records the delivery as failed
- **AND** does not crash the calling module
