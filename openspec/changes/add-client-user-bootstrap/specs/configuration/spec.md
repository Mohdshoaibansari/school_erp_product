## MODIFIED Requirements

### Requirement: auth.jwtExpirySeconds

The `auth.jwtExpirySeconds` configuration key SHALL hold the platform-wide JWT TTL in seconds, applied to every custom HS256 JWT minted by the platform's auth service. **Widened for the `client-user-bootstrap` capability:** the key SHALL ALSO govern the TTL of the Client Director's custom HS256 JWT. This makes the key serve DOUBLE-DUTY: it governs the platform owner's JWT TTL AND the client-leadership (CD) JWT TTL. The key defaults to `3600` (one hour) and can be tuned by the PO without code deploy via `PATCH /api/v1/config/keys/$KEY_ID`. Stale values are reloaded into the in-memory cache via the C-08 NOTIFY/LISTEN mechanism.

The widened role of this key is the NATURAL-EXPIRY SAFETY NET for the `client-user-bootstrap` capability's deferred token-revocation design (per D12 of the `client-user-bootstrap` PRD). When the PO suspends a CD, the CD's currently-issued HS256 JWT keeps working until its TTL elapses; the smaller the `auth.jwtExpirySeconds` value, the shorter the replay window. The key itself, its default value, and its edit authorization matrix are unchanged — only the documented consumption surface grows.

#### Scenario: CD JWT TTL equals auth.jwtExpirySeconds
- **WHEN** the auth service mints a CD's custom HS256 JWT
- **THEN** the JWT's `exp` claim SHALL equal `iat + auth.jwtExpirySeconds` (resolved via `config.get('auth.jwtExpirySeconds')` at mint time)

#### Scenario: PO tunes TTL without code change
- **WHEN** the PO PATCHes the `auth.jwtExpirySeconds` key default to a different value
- **THEN** the next CD login SHALL mint a JWT with the NEW TTL
- **AND** no code deploy SHALL be required (the value is resolved at mint time from the C-08 resolver)

#### Scenario: Suspended CD replay window
- **WHEN** the PO suspends a CD whose HS256 JWT was minted with TTL = `auth.jwtExpirySeconds`
- **THEN** the suspended CD's JWT SHALL keep authorizing until `exp` is reached
- **AND** the next login attempt by that CD SHALL be rejected because `lifecycle_status != "active"`
- **AND** the replay window is bounded by `auth.jwtExpirySeconds` (per D12)

#### Scenario: Key default unchanged
- **WHEN** the C-08 migration seeds `auth.jwtExpirySeconds`
- **THEN** its `default_value` SHALL remain `3600`
- **AND** the widening introduced by `client-user-bootstrap` SHALL NOT require a new migration seeding step