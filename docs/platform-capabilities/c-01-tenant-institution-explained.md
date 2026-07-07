# C-01: Tenant & Institution Management — Explained with Examples

> **Status:** Final  
> **Version:** 1.1  
> **Purpose:** Practical explanation of C-01 with real-world examples. Companion to the formal capability definition.  
> **Prerequisite Reading:** `platform-capabilities-v3.md` — C-01 section  
> **Cross-References:**  
> - [Main C-01 Definition](platform-capabilities-v3.md#c-01-tenant--institution-management)  
> - [Architecture — Tenant Model](../architecture/architecture-v1.md#3-tenant-hierarchy)  
>
> **Architecture note (v1.1):** C-01 has been split into two sub-capabilities: **C-01a Tenant Identity Infrastructure** (kernel — `kernel/repo_base.py`, `kernel/audit.py`, `kernel/transfer_coordinator.py`, `kernel/tenant_context.py`, `kernel/middleware.py`) and **C-01b Tenant & Institution Domain** (business — `business/tenant_institution/`). The infrastructure packages are consumed by every future business module; the domain logic is used only by C-01's own workflows. See the [Platform Capabilities v3](platform-capabilities-v3.md) Appendix A for the formal classification.  

---

## 1. What Is C-01 in Plain Language?

C-01 answers one fundamental question:

> **"Who is our customer, and which schools or colleges do they operate?"**

It is the **root capability** of the platform. Every single piece of data — every student, every attendance mark, every fee transaction — is tied back to this capability. Without it, you cannot know which school's data you are looking at.

### The Entities (What It Owns)

| Entity | Real-World Meaning |
|---|---|
| **PlatformOwner** | You — the company building and operating the SaaS platform |
| **Client** | The organization that signs the contract and pays the bills |
| **ClientLifecycle** | Where the client is in their journey: Prospect → Active → Suspended → Archived |
| **Institution** | An actual school, college, or university that teachers and students use daily |
| **InstitutionType** | Determines the default OrgUnit structure template applied when an institution is created. The client may modify this structure after setup to suit their needs. |
| **InstitutionLifecycle** | Where the institution is: Onboarding → Active → Inactive → Archived |
| **OrgUnit** | A structural unit within an institution: Department, Faculty, Grade, etc. |
| **OrgUnitHierarchy** | How OrgUnits relate to each other (parent-child) |

---

## 2. Example 1: Single School Client

**Scenario:** A small private school subscribes to your platform.

```
Platform Owner: SchoolERP Inc.
  └── Client: "Green Valley School"
       └── Institution: "Green Valley School"
              ├── OrgUnit: Academics
              │     ├── OrgUnit: Primary (Grade 1-5)
              │     │     ├── OrgUnit: Class 1A
              │     │     ├── OrgUnit: Class 1B
              │     │     └── OrgUnit: Class 2A
              │     └── OrgUnit: Secondary (Grade 6-12)
              └── OrgUnit: Administration
                    ├── OrgUnit: Accounts
                    └── OrgUnit: HR
```

Here the Client and Institution are effectively the same entity because the school itself is the paying customer.

### Lifecycle Walkthrough

| Step | Lifecycle State | What Happens |
|---|---|---|
| 1 | **Prospective** | SchoolERP creates a lead record for Green Valley School |
| 2 | **Onboarding** | Green Valley signs up. Admin configures Grades, Classes, Sections. Users are created. |
| 3 | **Active** | School goes live. Attendance, Homework, Fees modules are operational. |
| 4 | **Suspended** | *(If payment fails)* Access disabled. Data preserved. |
| 5 | **Archived** | *(If school permanently closes)* All data preserved for audit. Never deleted. |

---

## 3. Example 2: Multi-School Client (School Chain)

**Scenario:** A large educational trust operates multiple institutions under one contract.

```
Platform Owner: SchoolERP Inc.
  └── Client: "Vidya Bharati Educational Trust"
        ├── ClientLifecycle: Active
        │
        ├── Institution: "Vidya Bharati School – Indiranagar"
        │     ├── InstitutionType: School
        │     ├── InstitutionLifecycle: Active
        │     └── OrgUnits: Primary Section, Secondary Section
        │
        ├── Institution: "Vidya Bharati School – Whitefield"
        │     ├── InstitutionType: School
        │     ├── InstitutionLifecycle: Active
        │     └── OrgUnits: Primary Section, Secondary Section
        │
        ├── Institution: "Vidya Bharati School – Electronic City"
        │     ├── InstitutionType: School
        │     ├── InstitutionLifecycle: Onboarding    ← Being set up
        │     └── OrgUnits: (not yet configured)
        │
        └── Institution: "Vidya Bharati College – Indiranagar"
              ├── InstitutionType: College            ← Different type!
              ├── InstitutionLifecycle: Active
              └── OrgUnits: CS Dept, Commerce Dept, Admin
```

### What This Demonstrates

| Concept | How It Works Here |
|---|---|
| **One Client, Many Institutions** | Vidya Bharati Trust signs ONE contract. All four institutions live under it. |
| **Add Institutions Over Time** | Electronic City is in Onboarding. They can add a 5th school later without creating a new account. |
| **Mixed Institution Types** | The trust runs both Schools and a College. Different InstitutionTypes, same Client. |
| **Data Isolation** | A teacher at Indiranagar cannot see Whitefield data unless explicitly granted cross-school access. |

### How Billing Sees This (C-23 Integration)

```
Monthly Invoice to: "Vidya Bharati Educational Trust"
  ├── Attendance Module: 4 institutions × $50 = $200
  ├── Homework Module:  4 institutions × $40 = $160
  └── Fees Module:      1 institution × $60 = $60
  └── Total: $420
```

**One invoice to the client.** Itemized by institution. The trust decides internally how to allocate costs.

---

## 4. Example 3: How Other Capabilities Use C-01

Every action in the platform starts by asking: *"Which Client? Which Institution?"*

| Scenario | Question Asked | Answer Comes From C-01 |
|---|---|---|
| **A teacher logs in** | Which client does this user belong to? Which institutions can they access? | User → Client → Institution assignment |
| **Marking attendance** | For which institution? For which class (under which OrgUnit)? | Institution → OrgUnit hierarchy |
| **Sending a fee reminder** | Which institution's parents should receive this? | Institution context |
| **Running a report** | Single institution or all institutions under this client? | Client → Institutions |
| **Adding a new student** | Which institution does this student belong to? | Institution context |
| **Disabling a client** | Which institutions should become inaccessible? | Client → all its Institutions |

---

## 5. Example 4: Platform Owner's View

As the SaaS provider, here is how you see your business through C-01:

```
Platform Owner Dashboard
  ┌─────────────────────────────────────────────────────┐
  │ Total Clients: 47                                    │
  │ Total Institutions: 89                                │
  │                                                        │
  │ Client Breakdown:                                      │
  │ ├── Green Valley School          → 1 Institution      │
  │ ├── Vidya Bharati Trust          → 4 Institutions     │
  │ ├── Sunshine Academy             → 2 Institutions     │
  │ ├── Delhi Public School Chain    → 12 Institutions    │
  │ └── 43 other clients             → 70 Institutions    │
  │                                                        │
  │ Institutions by Type:                                  │
  │ ├── School:      82                                    │
  │ ├── College:     5                                     │
  │ └── University:  2                                     │
  │                                                        │
  │ Institutions by Lifecycle:                              │
  │ ├── Active:      78                                    │
  │ ├── Onboarding:  6                                     │
  │ ├── Inactive:    3                                     │
  │ └── Archived:    2                                     │
  └─────────────────────────────────────────────────────┘
```

---

## 6. Example 5: Adding a New School — Step by Step

**Scenario:** Vidya Bharati Trust opens a new branch. Here is the exact sequence.

### Step 1: Create the Institution Record

```
POST /api/clients/vidya-bharati/institutions
{
  "name": "Vidya Bharati School – HSR Layout",
  "type": "School",
  "address": "789, HSR Layout, Bangalore",
  "contactEmail": "hsr@vidyabharati.edu",
  "contactPhone": "+91-9876543210"
}

Response:
{
  "id": "inst-009",
  "lifecycle": "onboarding",    ← Starts in Onboarding
  "createdAt": "2026-06-07T10:30:00Z"
}
```

### Step 2: Configure OrgUnits

```
POST /api/institutions/inst-009/org-units
[
  { "name": "Primary Section",   "type": "SECTION", "children": ["1A","1B","2A"...] },
  { "name": "Secondary Section", "type": "SECTION", "children": ["9A","9B","10A"...] },
  { "name": "Administration",    "type": "DEPARTMENT", "children": ["Accounts", "HR"] }
]
```

### Step 3: Assign Users

The trust's Director already has access to all institutions (same Client). New teachers are created with scope restricted to `inst-009`.

### Step 4: Activate

```
PATCH /api/institutions/inst-009
{ "lifecycle": "active" }
```

The school goes live. Attendance, Homework, and other modules become operational.

### Step 5: Billing Updates Automatically

The next monthly invoice automatically includes the new school:

```
Invoice to: Vidya Bharati Educational Trust
  ├── Attendance: 5 institutions × $50 = $250    ← New school included
  ├── Homework:   5 institutions × $40 = $200
  └── Fees:       1 institution × $60 = $60
  └── Total: $510
```

No contract renegotiation. No account restructuring. Just a new institution under the existing client.

---

## 7. Example 6: Institution Closure — Data Preservation

**Scenario:** After 5 years, Vidya Bharati closes the Whitefield branch.

```
PATCH /api/institutions/inst-002
{ "lifecycle": "archived" }
```

### What Happens

| Aspect | Behavior |
|---|---|
| **Logins** | Users scoped ONLY to this institution can no longer log in |
| **Data** | All attendance records, fees, homework, etc. are preserved |
| **Reports** | Historical reports still show this institution's data |
| **Audit** | Every transaction remains in the audit trail |
| **Deletion** | ❌ Never happens. Data is immutable for audit compliance. |
| **Re-activation** | ✅ Possible — change lifecycle back to "active" |

---

## 8. What C-01 Does NOT Do

It is important to understand the boundaries of this capability:

| Concern | Owned By | Why Not C-01 |
|---|---|---|
| Who are the users? | C-02 Identity & User Management | Users exist within a client context but are managed separately |
| How do they log in? | C-03 Authentication | Login methods are configured per client, but the session logic is separate |
| What permissions do they have? | C-04 Authorization | Roles and permissions are scoped to institutions but managed by Authorization |
| What grades and classes exist? | C-05 Academic Structure | Academic hierarchy is a separate concern from organizational hierarchy |
| Which modules are active? | C-07 Subscription | A client may have 5 institutions but only 3 subscribed to a module |
| Where is the institution located? | C-13 Address Management | Addresses are managed separately to support multiple addresses per entity |

C-01 owns only the **Client, Institution, and their organizational hierarchy**. Everything else builds on top.

---

## 9. What Does InstitutionType Actually Do?

InstitutionType has **one purpose**: it determines the **default OrgUnit structure template** applied when an institution is created.

| InstitutionType | Default OrgUnit Template | Example |
|---|---|---| |
| School | Grades → Classes → Sections | Grade 1 → Class 1A, 1B |
| College | Programs → Batches | B.Sc. CS → Batch 2024 |
| University | Faculties → Departments → Programs → Batches | Science → CS → B.Sc. → Batch 2024 |
| Coaching Institute | Courses → Batches | JEE Prep → Batch A |

### After Creation, the Client Owns the Structure

Once the institution is created with its template, the client can:
- **Add** new OrgUnits (e.g., a school adding a "Pre-Primary" section)
- **Remove** OrgUnits that don't apply (e.g., removing "Hostel" if not applicable)
- **Restructure** the hierarchy (e.g., renaming "Section" to "Division")
- **Ignore** the template entirely and build from scratch

### What InstitutionType Does NOT Do

| It does NOT... | Why not... |
|---|---|
| Decide attendance mode (daily vs. subject-wise) | Attendance mode is a **module-level configuration** per institution or class |
| Control fee rules | Fee structures are defined independently by each institution |
| Affect authorization | Roles and permissions are not tied to institution type |
| Drive any runtime module behavior | All modules operate identically regardless of institution type |

**In short:** InstitutionType is a **setup-time convenience** — a starting template. It is not a runtime behavior driver.

---

## 10. Key Takeaways

| # | Principle | Why It Matters |
|---|---|---|
| 1 | **One Client, Many Institutions** | A school chain signs ONE contract. Adding schools does not require a new account. |
| 2 | **InstitutionType Drives OrgUnit Templates** | Each type provides a default OrgUnit structure (e.g., School → Grade/Class/Section, College → Program/Batch). Clients can modify this after creation. |
| 3 | **Lifecycle Management** | Institutions move through Onboarding → Active → Archived. Never deleted. Audit integrity preserved. |
| 4 | **Data Isolation is Automatic** | Institution A's data is invisible to Institution B — even within the same client — unless explicitly shared. |
| 5 | **No Duplicate Ownership** | No module defines its own "school" or "client" entity. C-01 is the single source of truth. |
| 6 | **Built First** | C-01 has no dependencies. It is the first capability built. Every other capability and module references it. |

---

> **End of Document**  
> **Version:** 1.0  
> **Part of:** `docs/platform-capabilities/`  
> **Next:** Similar explainer documents for C-02 through C-25 as needed
