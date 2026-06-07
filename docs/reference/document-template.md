# Document Template — School ERP Documentation Standards

> **Purpose:** This document defines the standard templates used across all School ERP documentation.  
> **Location:** docs/reference/document-template.md  
> **Applies To:** All documents under docs/architecture, docs/platform-capabilities, docs/requirements, docs/strategy

---

## 1. Document Header (All Documents)

Every document must begin with a metadata header block:

```markdown
# Document Title

> **Status:** [Draft | Review | Final | Superseded]
> **Version:** x.y
> **Last Updated:** YYYY-MM-DD
> **Author:** [Name / Role]
> **Source:** [Parent documents this is derived from, if any]
> **Purpose:** One-sentence description of this document's role.
> **Cross-References:**
> - [Related Document A](../path/to/document.md)
> - [Related Document B](../path/to/document.md)
```

---

## 2. Architecture Document Template

Used in: `docs/architecture/`

```markdown
# [Topic] — Architecture Decision Record

> **Status:** [Draft | Review | Final | Superseded]
> **Version:** x.y
> **Purpose:** Define architectural decisions, principles, and models for [topic].

---

## 1. Context

What problem or requirement drives this architectural decision?

## 2. Decision

What was decided and why?

## 3. Consequences

What are the implications — positive and negative?

## 4. Model

```
ASCII / UML diagram of the architectural model
```

## 5. Constraints

Non-negotiable constraints that this architecture imposes.

## 6. Alternatives Considered

| Alternative | Reason for Rejection |
|---|---|
| ... | ... |

## 7. Future Evolution

Under what conditions would this decision be revisited?
```

---

## 3. Capability Definition Template

Used in: `docs/platform-capabilities/`

```markdown
# C-XX: [Capability Name]

> **Layer:** [Kernel | Service | Pipeline]
> **Criticality:** [Critical | Important | Medium | Future]
> **Phase:** [1 | 2 | 3 | 4+]
> **Institution Scope:** [Agnostic | School-Optimized | Flexible]
> **Status:** [Draft | Review | Final]

---

## 1. Purpose

One paragraph explaining why this capability exists and what problem it solves.

## 2. Domain Ownership (Single Source of Truth)

| Entity | Description | Owned By |
|---|---|---|
| EntityName | Description of what this entity represents | This capability |
| EntityName2 | Description | This capability |

**This capability owns these entities. No other capability or module may duplicate or redefine them.**

## 3. Key Rules

1. Rule one — actionable, non-negotiable.
2. Rule two — ...
3. Rule three — ...

## 4. Dependencies

| Capability | Dependency Type | Rationale |
|---|---|---|
| C-XX | Required | This capability needs [entity] from C-XX |

## 5. Consumers

| Consumer Type | Examples |
|---|---|
| Business Modules | Attendance, Homework, Fees |
| Platform Capabilities | Authorization, Notification |

## 6. API Surface (Conceptual)

```
POST   /api/{client}/capability/resource
GET    /api/{client}/capability/resource
GET    /api/{client}/capability/resource/{id}
PUT    /api/{client}/capability/resource/{id}
DELETE /api/{client}/capability/resource/{id}
```

## 7. Data Model (Conceptual)

```json
{
  "id": "uuid",
  "tenantId": "uuid",
  "entity": {
    "field1": "value",
    "field2": "value"
  },
  "audit": {
    "createdAt": "timestamp",
    "updatedAt": "timestamp",
    "createdBy": "uuid"
  }
}
```

## 8. Configuration

| Key | Type | Default | Scope | Description |
|---|---|---|---|---|
| setting.name | boolean | true | Institution | Description |

## 9. Startup Scope (Phase [X])

What subset of this capability is built in the current phase. What is deferred.

## 10. Future Evolution

Under what conditions would this capability need to expand or change?
```

---

## 4. Requirements Document Template

Used in: `docs/requirements/`

```markdown
# [Module Name] — Functional Requirements

> **Status:** [Draft | Review | Final]
> **Version:** x.y
> **Purpose:** Define the functional scope of [module name].

---

## 1. Overview

Brief description of the module and its role in the platform.

## 2. User Stories

| ID | User | Story | Priority |
|---|---|---|---|
| FR-001 | Teacher | As a teacher, I want to ... so that ... | P0 |
| FR-002 | Parent | As a parent, I want to ... so that ... | P1 |

## 3. Functional Areas

### Area 1: [Name]

| ID | Feature | Description | Depends On |
|---|---|---|---|
| F-001 | Feature name | Description of the feature | Platform capabilities |

### Area 2: [Name]

| ID | Feature | Description | Depends On |
|---|---|---|---|

## 4. Business Rules

| Rule ID | Rule Description |
|---|---|
| BR-001 | Business rule description |

## 5. Platform Capability Dependencies

| Platform Capability | Required From Day 1? | Notes |
|---|---|---|
| C-01 Tenant Management | Yes | |

## 6. Out of Scope

Explicitly list what this requirements document does NOT cover.

## 7. Future Considerations

What might be added in later phases.
```

---

## 5. Strategy Document Template

Used in: `docs/strategy/`

```markdown
# [Topic] — Strategy Document

> **Status:** [Draft | Review | Final]
> **Version:** x.y
> **Purpose:** Define the strategic direction for [topic].

---

## 1. Strategic Objective

What are we trying to achieve?

## 2. Phased Approach

### Phase [N]: [Name]

| Aspect | Detail |
|---|---|
| Timeframe | Months X-Y |
| Focus | What is being built |
| Outcome | Measurable result |
| Success Metric | How we know it worked |

## 3. Decision Framework

What questions must be answered before proceeding with each phase?

## 4. Risk & Mitigation

| Risk | Impact | Mitigation |
|---|---|---|

## 5. Success Metrics

How do we measure success at each phase?
```

---

## 6. Naming Conventions

| Artifact | Convention | Example |
|---|---|---|
| Document files | `kebab-case.md` | `platform-capabilities-v3.md` |
| Capability IDs | `C-XX` | `C-06: Relationship Management` |
| Requirement IDs | `FR-XXX` | `FR-042: Parent attendance notification` |
| Version tags | `v1`, `v2`, `v3` | `platform-capabilities-v3.md` |
| Folders | `kebab-case` | `platform-capabilities/` |

---

## 7. Cross-Referencing Rules

1. **Reference by relative path:** `[Architecture v1](../architecture/architecture-v1.md)`
2. **Reference by ID for capabilities:** `C-06: Relationship Management Framework`
3. **Reference by section:** `[Tenant Model](../architecture/architecture-v1.md#3-tenant-hierarchy)`
4. **All cross-references must be verifiable** — broken links degrade document quality.

---

> **Template Version:** 1.0  
> **Applies To:** All documents under `docs/`
