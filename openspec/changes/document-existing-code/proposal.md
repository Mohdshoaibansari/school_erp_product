## Why

The School ERP codebase has accumulated significant implementation across kernel services (tenant, identity, auth, subscription, academic, etc.) but lacks corresponding ADRs and documentation that capture the architecture decisions and design rationale embodied in the code. Without this documentation, future contributors lack context for why things were built a certain way, increasing risk of regressions and inconsistent extensions.

## What Changes

- Create ADRs that document architectural decisions already reflected in the implemented code, distilling rationale, tradeoffs, and alternatives considered
- Produce service-level documentation describing what's implemented, the patterns used, and how services compose
- Organize documentation to align with existing code structure (kernel, modules, database)

## Capabilities

### New Capabilities

- `code-documentation`: Review implemented code across all packages and produce ADRs and service documentation that capture architectural decisions, design patterns, and rationale already embodied in the codebase.

### Modified Capabilities

*(None — this change documents existing behavior; no spec-level behavior changes.)*

## Impact

- ADRs will be added to `adr/` — no existing ADRs modified
- All documentation is additive; no code changes
- No API contracts, data models, or behavior are affected
