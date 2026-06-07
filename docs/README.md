# School ERP SaaS Platform — Documentation Index

> **Last Updated:** 2026-06-07  
> **Document Conventions:**
> - File names use **kebab-case** for consistency
> - Version suffixes (`-v1`, `-v3`) denote iteration
> - Cross-references use relative paths within `docs/`

---

## 📁 Folder Structure

```
docs/
├── README.md                          # ← This file — documentation index
│
├── architecture/                      # Architectural decisions & principles
│   └── architecture-v1.md             # Core architecture, tenant model, platform rules
│
├── requirements/                      # Functional capability catalogs
│   └── functional-requirements.md     # Master inventory of all 35+ functional areas
│
├── platform-capabilities/             # Shared platform capability definitions
│   └── platform-capabilities-v3.md    # Definitive reference — 25 capabilities, gap analysis
│
├── strategy/                          # Product & delivery strategy
│   └── startup-strategy.md            # Phased delivery, MVP roadmap, evolution strategy
│
└── reference/                         # Original / superseded documents (preserved for audit)
    ├── shared-platform-capabilities-v1.md   # Original draft
    ├── shared-platform-capabilities-v2.md   # Synthesis draft
    ├── architecture-v1.md                   # Original architecture doc
    ├── functional-requirements.md           # Original requirements
    └── startup-strategy.md                  # Original strategy doc
```

---

## 📄 Document Map

| Document | Location | Version | Status | Purpose |
|---|---|---|---|---|
| **Architecture v1** | `architecture/architecture-v1.md` | 1.0 | ✅ Final | Tenant model, data isolation, platform principles |
| **Functional Requirements** | `requirements/functional-requirements.md` | 1.0 | ✅ Final | Master catalog of all 35 functional areas with phase priorities |
| **Platform Capabilities v3** | `platform-capabilities/platform-capabilities-v3.md` | 3.0 | ✅ Current | 25 shared capabilities, gap analysis, dependency map, sequencing |
| **Startup Strategy** | `strategy/startup-strategy.md` | 1.0 | ✅ Final | Phased delivery, MVP roadmap, evolution stages |

---

## 🔗 Document Relationships

```
                      startup-strategy.md
                     (Phased Delivery Plan)
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
  functional-requirements   │     architecture-v1.md
  (What could be built)     │     (How it's structured)
            │               │               │
            └───────────────┼───────────────┘
                            ▼
              platform-capabilities-v3.md
         (Shared foundation — build this first)
                            │
                            ▼
                 Business Modules
         (Attendance, Homework, Fees, Exams...)
```

**Reading Order:**
1. **Startup Strategy** — Understand the phased approach and business priorities
2. **Architecture v1** — Understand the tenant model and design principles
3. **Platform Capabilities v3** — Understand what must be built before any module
4. **Functional Requirements** — Reference catalog for future module planning

---

## 📋 Key Decisions Recorded

| Decision | Document | Section |
|---|---|---|
| Modular Monolith (not microservices) | architecture-v1 | §3 |
| Shared database with tenant isolation | architecture-v1 | §11 |
| Analytics separated from transactional | architecture-v1 | §13 |
| Platform-first: build kernel before modules | platform-capabilities-v3 | Part I, §2 |
| Phase 1: 16 platform capabilities | platform-capabilities-v3 | Part V |
| Phase 2: Attendance, Homework, Fees, Parent Comm | startup-strategy | §2 |
| Client subdomain for tenant identification | architecture-v1 | §5.3 |

---

## ✏️ Document Creation Rules

When adding new documentation to this project:

1. **Place it in the correct subfolder** based on type (architecture, requirement, capability, strategy)
2. **Use kebab-case filenames** (e.g., `exam-management-module.md`)
3. **Add version suffix** for iterative documents (`-v1`, `-v2`)
4. **Update this README** with the new document's location and purpose
5. **Cross-reference** related documents using relative paths

---

## 📌 Next Documents to Create

Based on the current state:

| Priority | Document | Location | Description |
|---|---|---|---|
| 🥇 | `platform-capabilities/technical-specs/tenant-management-spec.md` | Platform Capabilities | Technical spec for C-01 |
| 🥇 | `platform-capabilities/technical-specs/user-management-spec.md` | Platform Capabilities | Technical spec for C-02 |
| 🥇 | `platform-capabilities/api-contracts/` | Platform Capabilities | API contracts per capability |
| 🥈 | `architecture/database-schema.md` | Architecture | Data model per capability |
| 🥈 | `architecture/technology-decisions.md` | Architecture | Stack decisions |
| 🥉 | `requirements/modules/attendance-module.md` | Requirements | Detailed Attendance spec |

---

> **Maintainer:** Platform Architecture Team  
> **Note:** Original source files remain in the project root for backward compatibility. All new work should use the `docs/` structure.
