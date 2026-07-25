## MODIFIED Requirements

### Requirement: Self-Visible Client RLS

The `client` table has no `client_id` column because the Client **is** the tenant (Q1, AC-14). The RLS policy on the `client` table itself SHALL be **self-visible**: a Client Director can read their own Client row via `id = current_client_id`, where `current_client_id` is resolved from the JWT/TenantContext (Q1, AC-14). Platform Owners can read all Clients (D11). No Client can read another Client's row (D1, AC-1).

The `client` table RLS policy SHALL include a bypass when `app.is_platform_owner = 'true'` is set in the session, allowing platform owner infrastructure lookups (e.g., subdomain-to-client resolution) to read all client rows (D14 platform-owner-separation).

Trace: Q1, AC-14, D1, AC-1, D14.

#### Scenario: Client Director reads own Client row
- **WHEN** a Client Director resolved to Client A requests the Client record
- **THEN** the RLS policy `id = current_client_id` returns only Client A's row; Client B's row is not visible (AC-14)

#### Scenario: Platform Owner reads any Client row
- **WHEN** a Platform Owner requests any Client record
- **THEN** the operation is permitted per D11 (all C-01 operations) (AC-14)

#### Scenario: Platform owner bypass via RLS session variable
- **WHEN** `SET LOCAL app.is_platform_owner = 'true'` is set
- **THEN** the RLS policy on the `client` table SHALL allow reading all client rows regardless of `current_client_id`

#### Scenario: Client cannot read another Client's row
- **WHEN** a Client Director resolved to Client A attempts to read Client B's row
- **THEN** the attempt is filtered by RLS and Client B's data is not returned (AC-1, AC-14)

### Requirement: API Shape — Subdomain-Resolved

C-01 APIs SHALL be subdomain-resolved: the Client is implicit from the subdomain (per D3), not embedded in the request path (Q5, AC-12). The illustrative client-in-path form (`POST /api/clients/{slug}/institutions`) shown in `docs/platform-capabilities/c-01-tenant-institution-explained.md` is SUPERSEDED by the subdomain-resolved form — it MUST NOT be used (Q5, AC-12).

Platform-Owner-only endpoints (Client create/suspend/terminate, ownership-transfer approval, InstitutionType management) SHALL live under a platform-scoped base (Q5, AC-12). The JWT/TenantContext carries both `client_id` (resolved from the subdomain at request start, via C-03) and a selected `institution_id` (set by the in-app institution switcher after login) per D1.

Platform owner SHALL be detected ONLY from the JWT claim `is_platform_owner: true` (D9 platform-owner-separation). The middleware SHALL NOT use DB role lookup or path prefix detection for platform owner identification. Platform endpoints remain at `/api/v1/platform/` but the path prefix no longer triggers `is_platform_owner=True` — only the JWT claim does.

Trace: Q5, D1, D9, AC-12.

#### Scenario: Institution creation is subdomain-resolved
- **WHEN** an authorized user creates an Institution under their Client
- **THEN** the request is `POST /api/v1/institutions` with the Client implicit from the subdomain; the Client is not embedded in the path (AC-12)

#### Scenario: Platform-Owner-only endpoints under a platform-scoped base
- **WHEN** a Platform Owner performs Client create/suspend/terminate, ownership-transfer approval, or InstitutionType management
- **THEN** those endpoints live under a platform-scoped base distinct from the client-portal subdomain base (AC-12)

#### Scenario: Platform owner detected from JWT claim only
- **WHEN** a request arrives at a platform-scoped endpoint
- **THEN** the middleware SHALL set `is_platform_owner=True` ONLY if the JWT contains `is_platform_owner: true`
- **AND** the middleware SHALL NOT detect platform owner from the path prefix alone

#### Scenario: Superseded client-in-path form is not used
- **WHEN** the API surface is designed or documented
- **THEN** the `POST /api/clients/{slug}/institutions` form is not used; the subdomain-resolved `POST /api/v1/institutions` form is authoritative (Q5, AC-12)
