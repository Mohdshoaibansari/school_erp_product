# configuration-framework Specification

## Purpose
TBD - created by archiving change add-c02-user-creation-activation. Update Purpose after archive.
## Requirements
### Requirement: app.activationBaseUrl

The system MUST seed a config key `app.activationBaseUrl` with type `string`, default `"http://127.0.0.1:8000"`, category `Business Rules`, module `app`. This key SHALL be used by user-creation services to construct the invite URL returned to the creator. The config SHALL be read at runtime via `config.get("app.activationBaseUrl")`. Per D3 and AGENTS.md §8.

#### Scenario: Key is seeded on migration
- **WHEN** the migration for this change is applied
- **THEN** `SELECT COUNT(*) FROM configuration_key WHERE key = 'app.activationBaseUrl'` returns 1
- **AND** the key's type is `string`
- **AND** the default value is `"http://127.0.0.1:8000"`
- **AND** the module is `app`

#### Scenario: Invite URL uses config value in production
- **GIVEN** `app.activationBaseUrl` is set to `"https://app.school-erp.com"` at the platform scope
- **WHEN** any user creation endpoint builds an invite URL
- **THEN** the URL SHALL start with `"https://app.school-erp.com"`
- **AND** SHALL NOT use the seeded default

#### Scenario: Config change takes effect immediately (no restart required)
- **GIVEN** the platform is running with `app.activationBaseUrl = "http://127.0.0.1:8000"`
- **WHEN** the config value is updated to `"https://staging.school-erp.com"` via the config API or admin interface
- **THEN** subsequent user creations SHALL use the new URL without requiring an application restart
- **AND** the audit trail SHALL record who changed the value and when

#### Scenario: Fallback to default when key is missing
- **GIVEN** the `app.activationBaseUrl` key exists in `configuration_key` but no override value is set
- **WHEN** `config.get("app.activationBaseUrl")` is called
- **THEN** the call SHALL return the seeded default `"http://127.0.0.1:8000"`

---

### Requirement: Config key migration follows AGENTS.md §8

The migration that seeds `app.activationBaseUrl` SHALL be a new Alembic revision in `backend/migrations/versions/`. It SHALL NOT modify existing seed data or existing migrations. The migration SHALL insert into `configuration_key` with the correct type, default value, category, module, and description. Per AGENTS.md §8.

#### Scenario: Migration is independent
- **WHEN** the migration is inspected
- **THEN** it SHALL be a new file (not an edit to an existing migration)
- **AND** it SHALL only contain the `app.activationBaseUrl` seed (and any other config keys scoped to this change)
- **AND** it SHALL use `op.execute()` with a raw SQL INSERT or the SQLAlchemy model approach matching existing config-seeding patterns

