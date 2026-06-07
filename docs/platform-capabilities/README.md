# Platform Capabilities — Index

> **Folder:** `docs/platform-capabilities/`  
> **Purpose:** Define every shared platform capability that business modules consume.

---

## Documents in This Folder

| File | Version | Status | Description |
|---|---|---|---|
| `platform-capabilities-v3.md` | 3.0 | ✅ Current | Definitive reference — 25 capabilities, gap analysis, dependency map |
| `c-01-tenant-institution-explained.md` | 1.0 | ✅ Current | Practical explanation of C-01 with real-world examples |
| `README.md` | 1.0 | ✅ Current | This index |

---

## Upcoming Documents

| Document | Description |
|---|---|
| `technical-specs/tenant-management-spec.md` | Technical spec for C-01 |
| `technical-specs/user-management-spec.md` | Technical spec for C-02 |
| `api-contracts/` | API contract definitions per capability |

---

## Capability Classification Reference

| Layer | Description | Examples |
|---|---|---|
| **Kernel** | Every module requires it | Tenant, Users, Auth, Academic Structure |
| **Service** | Most modules use it | Notification, Document, Search |
| **Pipeline** | Data processing & reporting | Analytics, Billing |

| Criticality | Meaning |
|---|---|
| Critical | Must exist before any business module |
| Important | Should exist before business module reaches production maturity |
| Medium | Can be deferred but adds significant value |
| Future | Planned for later phases |

---

## Quick Reference: 25 Capabilities

| ID | Capability | Layer | Criticality | Phase |
|---|---|---|---|---|
| C-01 | Tenant & Institution Management | Kernel | Critical | 1 |
| C-02 | Identity & User Management | Kernel | Critical | 1 |
| C-03 | Authentication | Kernel | Critical | 1 |
| C-04 | Authorization | Kernel | Critical | 1 |
| C-05 | Academic Structure Framework | Kernel | Critical | 1 |
| **C-06** | **Relationship Management Framework** | **Kernel** | **Critical** | **1** |
| C-07 | Subscription Management | Kernel | Critical | 1 |
| C-08 | Configuration Framework | Kernel | Critical | 1 |
| C-09 | Notification Framework | Service | Critical | 1 |
| C-10 | Communication Framework | Service | Important | 1 |
| C-11 | Audit & Observability Framework | Kernel | Critical | 1 |
| **C-12** | **Code & Identifier Generation Engine** | **Service** | **Important** | **1** |
| **C-13** | **Location & Address Management** | **Service** | **Important** | **1** |
| C-14 | Document Management Framework | Service | Important | 1 |
| C-15 | Workflow Framework | Service | Important | 2 |
| **C-16** | **Calendar & Scheduling Framework** | **Service** | **Important** | **2** |
| **C-17** | **Dynamic Group Management** | **Service** | **Important** | **2** |
| **C-18** | **Bulk Operations Framework** | **Service** | **Important** | **2** |
| **C-19** | **Export & Document Generation Engine** | **Service** | **Important** | **2** |
| **C-20** | **Task & Reminder Framework** | **Service** | Medium | 3 |
| C-21 | Search Framework | Service | Medium | 3 |
| C-22 | Analytics Framework & Data Pipeline | Pipeline | Important | 2 |
| C-23 | Billing Framework | Pipeline | Important | 2 |
| C-24 | Integration Framework | Service | Important | 1 |
| C-25 | AI Framework | Service | Future | 6+ |

> **Bold** = New capability identified in v3 gap analysis (not in original documents)
