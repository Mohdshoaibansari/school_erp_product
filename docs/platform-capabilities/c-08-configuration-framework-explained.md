# C-08: Configuration Framework — Explained with Examples

> **Status:** Final  
> **Version:** 1.0  
> **Purpose:** Practical explanation of C-08 with real-world examples. Companion to the formal capability definition.  
> **Prerequisite Reading:** `platform-capabilities-v3.md` — C-08 section  
> **Cross-References:**  
> - [Main C-08 Definition](platform-capabilities-v3.md#c-08-configuration-framework)  
> - [C-01: Tenant & Institution Management](c-01-tenant-institution-explained.md) — scope hierarchy depends on Client and Institution  

---

## 1. What Is C-08 in Plain Language?

C-08 answers one fundamental question:

> **"How should the platform behave, and for whom?"**

It is the **centralized settings system** of the platform. Every configurable behavior — from attendance cutoff times to date formats to feature flags — flows through C-08. Without it, every setting would be hardcoded, requiring code changes and redeployment for even the smallest adjustment.

### The Entities (What It Owns)

| Entity | Real-World Meaning |
|---|---|
| **ConfigurationKey** | A named setting with a typed value (e.g., `attendance.markingCutoffTime`) |
| **ConfigurationValue** | The value at a specific scope level (e.g., `"11:00 AM"` for Indiranagar) |
| **ConfigurationScope** | The level at which a value applies: Platform → Client → Institution → Module |
| **FeatureToggle** | A named on/off switch for features (e.g., `"advancedAnalytics"` = true) |

---

## 2. Example 1: The Problem C-08 Solves

**Without C-08 (hardcoded):**

```javascript
// Every value is baked into the code
const ATTENDANCE_CUTOFF = "10:00 AM";
const LATE_FEE_PERCENT = 2;
const DATE_FORMAT = "DD/MM/YYYY";
const MAX_FILE_UPLOAD_MB = 10;
```

To change the attendance cutoff from 10:00 AM to 11:00 AM, a developer must:
1. Change the code
2. Run tests
3. Deploy to production
4. Restart the application

**With C-08 (configurable):**

```javascript
// Values are read from the configuration store
const ATTENDANCE_CUTOFF = config.get("attendance.markingCutoffTime");
const LATE_FEE_PERCENT = config.get("fee.lateFeePercentage");
const DATE_FORMAT = config.get("display.dateFormat");
const MAX_FILE_UPLOAD_MB = config.get("platform.maxFileUploadMB");
```

To change the attendance cutoff:
1. Admin opens the Configuration panel
2. Changes the value
3. Saves

**No code change. No deployment. No restart.** The change takes effect immediately.

---

## 3. Example 2: Scope Inheritance — The Core Concept

This is the most important concept in C-08. Settings **cascade** from global to specific:

```
Platform (Global Defaults)       ← highest priority fallback
  └── Client Overrides           ← overrides platform for a client
       └── Institution Overrides ← overrides client for an institution
            └── Module Overrides ← overrides institution for a module
```

### Real-World Scenario: Attendance Cutoff Time

**Platform Default:**
```
attendance.markingCutoffTime = "10:00 AM"
```

**Green Valley School (Client) does NOT set this value.** It inherits from Platform.

**Green Valley – Indiranagar (Institution) sets an override:**
```
attendance.markingCutoffTime = "11:00 AM"
```

**Green Valley – Whitefield (Institution) does NOT set this value.** It inherits from Platform.

### Result

| Institution | Resolved Value | Source |
|---|---|---|
| Green Valley – Indiranagar | `11:00 AM` | Institution override |
| Green Valley – Whitefield | `10:00 AM` | Platform default (inherited) |

**Same platform. Same code. Different behavior per institution.**

### Visualizing the Inheritance

```
Platform: attendance.markingCutoffTime = "10:00 AM"
│
├── Client: Green Valley School
│   │  (no override — inherits "10:00 AM" from Platform)
│   │
│   ├── Institution: Indiranagar
│   │   attendance.markingCutoffTime = "11:00 AM"  ← OVERRIDE
│   │   Resolved: "11:00 AM" (from Institution)
│   │
│   └── Institution: Whitefield
│       (no override — inherits "10:00 AM" from Platform)
│       Resolved: "10:00 AM" (from Platform)
```

---

## 4. Example 3: Configuration Categories in Action

C-08 manages settings across five categories. Here's how each works in practice:

### Business Rules

| Key | Default Value | Institution Override | Why Override? |
|---|---|---|---|
| `attendance.markingCutoffTime` | `"10:00 AM"` | `"11:00 AM"` | Indiranagar starts classes later |
| `fee.lateFeePercentage` | `2` | `1.5` | Whitefield has a more lenient policy |
| `leave.autoApproveUnderDays` | `3` | `5` | College allows longer auto-approval |

### Display Settings

| Key | Default Value | Client Override | Why Override? |
|---|---|---|---|
| `display.dateFormat` | `"DD/MM/YYYY"` | `"MM/DD/YYYY"` | US-based client |
| `display.timezone` | `"Asia/Kolkata"` | `"Asia/Dubai"` | Dubai-based school |
| `display.language` | `"en"` | `"hi"` | Hindi-medium school |

### Academic Settings

| Key | Default Value | Institution Override | Why Override? |
|---|---|---|---|
| `academic.gradingScale` | `"percentage"` | `"CGPA"` | College uses CGPA |
| `academic.passPercentage` | `33` | `40` | Stricter passing criteria |
| `academic.termStructure` | `"yearly"` | `"semester"` | College follows semesters |

### Notification Rules

| Key | Default Value | Client Override | Why Override? |
|---|---|---|---|
| `notification.attendanceAbsenceAlert` | `true` | `false` | Client prefers manual alerts |
| `notification.defaultChannel` | `"email"` | `"sms"` | SMS has better reach |
| `notification.digestFrequency` | `"daily"` | `"weekly"` | Reduce notification fatigue |

### Feature Toggles

| Key | Default Value | Client Override | Why Override? |
|---|---|---|---|
| `feature.advancedAnalytics` | `false` | `true` | Premium add-on enabled |
| `feature.transportModule` | `true` | `false` | Client doesn't use transport |
| `feature.aiLessonPlanning` | `false` | `true` | Beta feature enabled for trial |

---

## 5. Example 4: How Other Capabilities Use C-08

Every capability and module reads configuration from C-08 instead of hardcoding values:

| Capability | Configuration Key | Default | Used For |
|---|---|---|---|
| **C-01: Tenant** | `institution.maxOrgUnitDepth` | `5` | Prevents infinite OrgUnit nesting |
| **C-02: Identity** | `user.sessionTimeoutMinutes` | `30` | Auto-logout after inactivity |
| **C-03: Auth** | `auth.passwordMinLength` | `8` | Password policy enforcement |
| **C-04: Authz** | `authz.maxRolesPerUser` | `5` | Prevents role explosion |
| **C-05: Academic** | `academic.maxClassesPerTeacher` | `3` | Workload limits |
| **C-07: Subscription** | `subscription.trialDays` | `14` | Free trial duration |
| **Attendance** | `attendance.markingCutoffTime` | `"10:00 AM"` | When marking closes |
| **Fees** | `fee.lateFeePercentage` | `2` | Late payment penalty |
| **Homework** | `homework.maxAttachmentsPerAssignment` | `5` | File upload limit |
| **Exams** | `exam.moderationMaxMarksAdjustment` | `10%` | Grade moderation cap |

### How a Module Reads Configuration

```javascript
// Attendance Module — marking attendance
async function markAttendance(studentId, status, markedBy) {
  // 1. Read the cutoff time from C-08
  const cutoffTime = await config.get("attendance.markingCutoffTime", {
    scope: {
      type: "institution",
      id: getCurrentInstitutionId()
    },
    fallback: "10:00 AM"  // Platform default if nothing is set
  });

  // 2. Check if current time is before cutoff
  const now = new Date();
  const cutoff = parseTime(cutoffTime);

  if (now > cutoff) {
    throw new Error(`Attendance marking closed at ${cutoffTime}`);
  }

  // 3. Proceed with marking
  await saveAttendance(studentId, status, markedBy);
}
```

The Attendance module **does not know or care** what the cutoff time is. It simply asks C-08: *"What's the cutoff for this institution?"* and acts on the answer.

---

## 6. Example 5: Platform Owner's View

As the SaaS provider, C-08 gives you a single pane of glass for all platform behavior:

```
Configuration Dashboard
  ┌─────────────────────────────────────────────────────────────────┐
  │ Platform-Level Defaults                                         │
  │ ├── attendance.markingCutoffTime:    "10:00 AM"                 │
  │ ├── fee.lateFeePercentage:          2                          │
  │ ├── display.dateFormat:             "DD/MM/YYYY"                │
  │ ├── notification.defaultChannel:    "email"                     │
  │ ├── feature.advancedAnalytics:      false                      │
  │ └── feature.transportModule:        true                       │
  │                                                                  │
  │ Client Overrides: 12 clients have custom settings               │
  │ Institution Overrides: 34 institutions have custom settings     │
  │                                                                  │
  │ Recent Changes:                                                  │
  │ ├── 2026-06-07 14:30  Green Valley  fee.lateFeePercentage → 1.5│
  │ ├── 2026-06-07 11:15  Vidya Bharati  attendance.cutoff → 11AM  │
  │ └── 2026-06-06 09:00  Platform Admin  feature.aiLesson → true  │
  └─────────────────────────────────────────────────────────────────┘
```

---

## 7. Example 6: Adding a New Configuration — Step by Step

**Scenario:** The product team decides to add a new configurable setting: "Allow students to submit homework after the deadline?"

### Step 1: Define the Configuration Key

```
POST /api/config/keys
{
  "key": "homework.allowLateSubmission",
  "type": "boolean",
  "defaultValue": false,
  "description": "Allow students to submit homework after the deadline",
  "category": "Business Rules",
  "module": "homework"
}

Response:
{
  "id": "cfg-045",
  "key": "homework.allowLateSubmission",
  "type": "boolean",
  "defaultValue": false,
  "createdAt": "2026-06-07T10:00:00Z"
}
```

### Step 2: Platform Default Is Active Immediately

All institutions now inherit `false` — late submission is not allowed. No code deployment needed.

### Step 3: Client Override (Optional)

Green Valley School wants to allow late submission for their institutions:

```
POST /api/config/values
{
  "key": "homework.allowLateSubmission",
  "scope": { "type": "client", "id": "client-green-valley" },
  "value": true
}
```

Now all Green Valley institutions allow late submission. Other clients still block it.

### Step 4: Institution Override (Optional)

Within Green Valley, the Primary Wing doesn't want late submission:

```
POST /api/config/values
{
  "key": "homework.allowLateSubmission",
  "scope": { "type": "institution", "id": "inst-green-valley-primary" },
  "value": false
}
```

### Final Resolution

| Scope | Value | Source |
|---|---|---|
| Platform | `false` | Default |
| Green Valley (Client) | `true` | Client override |
| Green Valley – Indiranagar | `true` | Inherited from Client |
| Green Valley – Primary Wing | `false` | Institution override |

### Step 5: Audit Trail

```
GET /api/config/audit?key=homework.allowLateSubmission

[
  {
    "timestamp": "2026-06-07T10:00:00Z",
    "action": "key_created",
    "by": "platform-admin",
    "value": false
  },
  {
    "timestamp": "2026-06-07T14:30:00Z",
    "action": "value_set",
    "scope": "client:green-valley",
    "by": "green-valley-admin",
    "value": true
  },
  {
    "timestamp": "2026-06-07T15:00:00Z",
    "action": "value_set",
    "scope": "institution:green-valley-primary",
    "by": "green-valley-admin",
    "value": false
  }
]
```

Every change is recorded. Who changed what, when, and at what scope.

---

## 8. Example 7: Feature Toggle — Gradual Rollout

**Scenario:** You're launching "AI Lesson Planning" as a premium feature. You want to:
1. Enable it only for paying clients
2. Gradually roll it out to trial users

### Step 1: Define the Feature Toggle

```
POST /api/config/keys
{
  "key": "feature.aiLessonPlanning",
  "type": "boolean",
  "defaultValue": false,
  "description": "Enable AI-powered lesson planning assistant",
  "category": "Feature Toggles",
  "module": "lesson-planning"
}
```

### Step 2: Enable for Premium Clients

```
POST /api/config/values
{
  "key": "feature.aiLessonPlanning",
  "scope": { "type": "client", "id": "client-premium-school-1" },
  "value": true
}
```

### Step 3: Enable for All Clients (Gradual Rollout)

After testing, you enable it platform-wide:

```
PATCH /api/config/keys/feature.aiLessonPlanning
{
  "defaultValue": true
}
```

Now everyone gets it by default. But you can still disable it for specific clients:

```
POST /api/config/values
{
  "key": "feature.aiLessonPlanning",
  "scope": { "type": "client", "id": "client-budget-school" },
  "value": false
}
```

### Resolution

| Scope | Value | Why |
|---|---|---|
| Platform | `true` | Default enabled |
| Premium School | `true` | Inherited from Platform |
| Budget School | `false` | Explicitly disabled |

---

## 9. What C-08 Does NOT Do

It is important to understand the boundaries of this capability:

| Concern | Owned By | Why Not C-08 |
|---|---|---|
| Database connection strings | Environment Variables | App-level infrastructure config stays in env vars |
| API keys for external services | C-19 Integration Framework | Integration secrets are managed by the integration layer |
| User preferences (theme, language) | C-02 Identity & User Management | Per-user display preferences are user-level, not platform-level |
| Module-specific business logic | Business Modules | C-08 stores the *value*, modules implement the *behavior* |
| Data storage | Database | C-08 stores configuration, not application data |
| Deployment configuration | DevOps / CI-CD | Server config, scaling rules, etc. are infrastructure concerns |

C-08 owns **runtime-configurable behavior settings** — nothing more.

---

## 10. Key Takeaways

| # | Principle | Why It Matters |
|---|---|---|
| 1 | **No Code Deploy for Config Changes** | Admin changes a setting → takes effect immediately. Zero downtime. |
| 2 | **Scope Inheritance** | Set a default once at Platform level. Override only where needed. Saves effort. |
| 3 | **Typed Values with Validation** | String, number, boolean, JSON, date — type safety prevents misconfiguration. |
| 4 | **Audit Trail** | Every change records who, what, when. Compliance and debugging. |
| 5 | **Feature Toggles** | Gradual rollout, premium add-ons, beta features — all without code changes. |
| 6 | **Modules Read, Don't Own** | Modules consume configuration from C-08. No module defines its own settings store. |
| 7 | **Built Early** | C-08 is a Level 1 capability — no dependencies. Built before any business module. |

---

## 11. How C-08 Relates to Other Capabilities

```
C-08: Configuration Framework
  │
  ├── Provides settings to → C-01 (Tenant)
  │     └── e.g., maxOrgUnitDepth, institutionLifecycle rules
  │
  ├── Provides settings to → C-02 (Identity)
  │     └── e.g., sessionTimeout, passwordPolicy
  │
  ├── Provides settings to → C-03 (Auth)
  │     └── e.g., allowedLoginMethods, mfaRequired
  │
  ├── Provides settings to → C-04 (Authz)
  │     └── e.g., maxRolesPerUser, delegationEnabled
  │
  ├── Provides settings to → Attendance Module
  │     └── e.g., markingCutoffTime, absenceAlertEnabled
  │
  ├── Provides settings to → Fees Module
  │     └── e.g., lateFeePercentage, autoReminderEnabled
  │
  └── Provides settings to → Every other capability and module
```

**C-08 is the nervous system of platform configurability.** Every capability that needs to be configurable reads from C-08.

---

> **End of Document**  
> **Version:** 1.0  
> **Part of:** `docs/platform-capabilities/`  
> **Next:** Similar explainer documents for C-02, C-03, C-04, C-05, etc. as needed
