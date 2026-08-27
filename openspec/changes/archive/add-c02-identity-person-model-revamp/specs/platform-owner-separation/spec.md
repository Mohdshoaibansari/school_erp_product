# Delta Spec — Platform Owner Separation (Person-Model Revamp)

> **Change:** `add-c02-identity-person-model-revamp`
> **Domain:** platform-owner-separation
> **Delta type:** MODIFIED (minimal)
> **Base spec:** `openspec/specs/platform-owner-separation/spec.md`
> **Source ADR:** `docs/architecture/adr-c02-identity-person-model-revamp.md` (D6a, D3d)
> **Source PRD:** `docs/prd/c02-identity-person-model-revamp.md` (AC-13)

---

## MODIFIED Requirements (minimal)

### REQ-POS-01: Platform Owner Discovery via is_platform_owner (Modified — category removed)

The Platform Owner SHALL exist only in Supabase Auth with `user_metadata.is_platform_owner = true` and MUST NOT have a row in `app_user` — this is **already** the model in the archived spec and is unchanged. The revamp's contribution is that **no residual `user_category`-based discovery code SHALL remain**. Platform Owner discovery SHALL use the `is_platform_owner` flag/claim exclusively (AC-13). Per D6a.

#### Scenario: PO discovered by flag (unchanged, reinforced)
- **WHEN** the system checks whether a user is a Platform Owner
- **THEN** it SHALL check the `is_platform_owner` flag/claim
- **AND** SHALL NOT consult any `user_category` value (the column no longer exists)

#### Scenario: PO has no app_user row (unchanged)
- **WHEN** a Supabase Auth user with `user_metadata.is_platform_owner = true` logs in
- **THEN** the system SHALL skip the `app_user` table lookup entirely
- **AND** return a JWT with `{sub: <user_id>, is_platform_owner: true}`

---

### REQ-POS-02: Platform Owner ↔ Person Linkage (Modified — design clarification)

The PO exists only in Supabase Auth (no `app_user`, no `client_user` row). Whether the PO gets a `person` row for their own human data is an **open design clarification** (PRD §3 implies "PO's own human data now lives on `person`" but no AC covers it). This delta flags the clarification for the design phase. Per D3a, D6a.

> **Design clarification needed (deferred to design.md):** Does the PO (who has no account row) get a `person` row? If yes, how is it linked (the PO has no `app_user.person_id`/`client_user.person_id`)? Options: (a) PO gets a `person` row linked via a PO-specific mechanism; (b) PO has no `person` row (human data is not modeled for the PO in this revamp). This is minor — the PO is a single SaaS operator, not a domain entity.

#### Scenario: TODO — clarify PO↔person linkage in design
- **GIVEN** the design phase addresses PRD §3's implication
- **WHEN** the PO↔person linkage is decided
- **THEN** the requirement SHALL be finalized here
