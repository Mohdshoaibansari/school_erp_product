## ADDED Requirements

### Requirement: Hidden module gating for free tier
Feature: Module Gating
Rule: Modules not included in the free tier are completely invisible — no upsell, no disabled buttons

#### Scenario: Free tier user sees only free modules in navigation
- **GIVEN** a user from a free-tier client
- **WHEN** they view the application navigation menu
- **THEN** they see only Students, Attendance, and Fees
- **AND** they do not see Exams, Homework, Transport, Communication, or Timetable
- **AND** no lock icons, upgrade banners, or disabled menu items are displayed

#### Scenario: Free tier user cannot access paid module URLs
- **GIVEN** a user from a free-tier client
- **WHEN** they navigate directly to a paid module URL (e.g., /exams)
- **THEN** the system returns a 404 or redirects to the dashboard
- **AND** no mention of the module is shown in the error

#### Scenario: Frontend hides paid modules at build time
- **GIVEN** a single frontend build serving all tenants
- **WHEN** the frontend loads for a free-tier client
- **THEN** paid module code is not rendered
- **AND** the frontend obtains module availability from a runtime API endpoint

#### Scenario: API rejects paid module requests for free tier
- **GIVEN** a free-tier client
- **WHEN** a request is made to a paid module API endpoint (e.g., POST /api/exams)
- **THEN** the API returns a 403 Forbidden
- **AND** the response does not reveal what module was blocked

### Requirement: Module availability is data-driven
Feature: Module Gating
Rule: Module availability is driven by subscription data, not hardcoded per tenant

#### Scenario: Adding a new module does not require frontend changes
- **GIVEN** the platform defines a new module "Library"
- **WHEN** a paid client's subscription includes the Library module
- **THEN** the module appears automatically in the navigation
- **AND** no code deployment is needed to show it

#### Scenario: Module removal is immediate
- **GIVEN** a paid client subscribed to the Homework module
- **WHEN** their subscription is updated to remove Homework
- **THEN** the Homework module disappears from navigation on next page load
- **AND** existing Homework data is preserved in the database
- **AND** API access to Homework endpoints returns 403
