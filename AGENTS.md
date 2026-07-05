# AGENTS.md

> Operational context for AI agents working in this repo. Evergreen process — not status.

---

## 1. Two Sources of Truth — divided by purpose

This repo uses TWO sources of truth. Do not mix their roles.

### `docs/` — Decision-making + stable reference
- **Brainstorming and decisions happen here**, WITHOUT sdd-stack involvement.
- **ADRs** (architectural decision records) live in `docs/architecture/adr-<capability>-implementation.md`.
- Stable reference lives here: architecture principles (`architecture-v1.md`), capability catalog (`platform-capabilities-v3.md`), requirements catalog (`functional-requirements.md`), strategy (`startup-strategy.md`), templates (`reference/`).
- `docs/` is NOT frozen — it is the ongoing home for decisions and reference. New ADRs are added as decisions are made.
- A capability's "explained" deep-dive (e.g. `c-XX-*-explained.md`) is **superseded** once that capability's OpenSpec spec is archived: add a "Superseded by OpenSpec spec `<change-id>`" note at the top and point to the archived spec.

### `openspec/` — Behavioral source of truth (change-tracked)
- OpenSpec is the source of truth for **what the system does** (behavioral specs + change deltas).
- Specs are deltas inside an active change folder (`openspec/changes/<change-id>/specs/<domain>/spec.md`), NOT standalone files.
- **Never edit `openspec/specs/` directly during an active feature** — only delta specs inside the change.
- OpenSpec is fed from `docs/` decisions, one capability at a time.

---

## 2. Capability-at-a-Time Workflow

Capabilities are implemented **one at a time**, in this strict order. Do not start the next capability until the previous one is archived.

### Phase 1 — Brainstorm (in `docs/`, NO sdd-stack)
1. Brainstorm the capability's implementation decisions with the user in chat.
2. Capture the decisions as an ADR: `docs/architecture/adr-<capability>-implementation.md` (follow `docs/reference/document-template.md` §2).
3. Resolve every open implementation question, one at a time, and record each resolution in the ADR.
4. Commit the ADR.
5. **Do NOT touch OpenSpec until the ADR is final and committed.**

### Phase 2 — Feed to sdd-stack (OpenSpec)
6. Once the ADR is final, feed **only that capability's decisions** to the sdd-stack subagent.
7. sdd-stack runs its full lifecycle, each phase delegated to a subagent:
   - PRD → `sdd-stack-feature-prd`
   - Impact classification → `sdd-stack-impact-classification`
   - Proposal → spec deltas → design → tasks → `sdd-stack-prd-to-sdd`
   - Apply → `sdd-stack-apply`
   - Verify → `sdd-stack-verify`
   - Archive → `sdd-stack-archive`
8. The capability is "done" only after **archive** completes.

### Phase 3 — Next capability (return to Phase 1)
9. After archive, return to Phase 1 for the next capability.
10. **Never start the next brainstorm until the previous capability is archived.**

---

## 3. Change Loop — modifying a spec mid-lifecycle

If at **ANY** phase of sdd-stack a change is needed:

1. **Stop the sdd-stack phase.**
2. Make the change in `docs/` first — edit the ADR or add a new ADR.
3. Commit the `docs/` change.
4. Feed the change to sdd-stack to modify the spec and re-implement.
5. **Never edit `openspec/` specs directly without the change being recorded in `docs/` first.**

This invariant is non-negotiable: `docs/` is always the decisional input; OpenSpec specs are always derived from it.

---

## 4. Branch Discipline

- **Implementation must happen on `main` branch only.**
- Before running `/opsx-apply`, check current branch with `git branch --show-current`.
- If not on `main`, **stop and remind the user** to switch to main first.
- Syncing specs to main (`/opsx-sync`) happens **after** implementation confirms specs are correct, not before.
- One spec at a time: sync a single capability spec to main, implement it, verify, then move to the next.
- Brainstorming and ADR authoring (`docs/`) can happen on any branch — it is planning, not implementation.
- OpenSpec must be initialized (`openspec init --tools pi`) before the first capability is fed to sdd-stack.

---

## 5. OpenSpec Workflow

- For OpenSpec propose/apply/verify/archive workflows, use the local `openspec-git-discipline` skill to enforce proposal commits before apply and merge-before-archive discipline.
- The sdd-stack transformation chain is: `prd.md → proposal.md → specs/**/spec.md → design.md → tasks.md → apply → verify.md → archive`.
- OpenSpec is the source of truth; specs are deltas inside the active change.

---

## 6. SDD Delegation Rule

- The parent session **orchestrates**; it does **NOT** execute SDD phases locally.
- The parent may clarify scope in-chat only.
- Before any repo exploration, drafting, or implementation for a routed SDD phase, **delegate to the matching subagent or `/sdd-stack:*` command**.
- If about to use `read`/`bash`/`edit`/`write` in the parent for a routed SDD phase, **STOP and delegate instead**.
- Delegation is not optional once complexity appears.

---

## 7. ADR Pattern

- Every capability's implementation decisions are captured as an ADR **before** feeding to sdd-stack.
- ADRs live in `docs/architecture/adr-<capability>-implementation.md`.
- ADRs follow the repo's ADR template (`docs/reference/document-template.md` §2): Context / Decision / Consequences / Model / Constraints / Alternatives / Future Evolution.
- ADRs are decisional **input** to the OpenSpec spec/design — they are **NOT** the spec itself.
- Open questions surfaced during sdd-stack are resolved back into the ADR (Change Loop, §3), not directly into specs.

---

## 8. Current decisional state

| Capability | ADR | Status | Next |
|---|---|---|---|
| C-01 Tenant & Institution Management | `docs/architecture/adr-c01-tenant-institution-implementation.md` | Decisions final (12 ADR decisions + 10 spec resolutions) | Feed to sdd-stack (Phase 2) |

> This table is the single place to check "where are we." Update it as capabilities move through phases.

---
