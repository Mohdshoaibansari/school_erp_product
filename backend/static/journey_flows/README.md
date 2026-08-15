# School ERP Test Console — Scenario UI v3

This is a static frontend shell around the existing API flow pages.

## Design decisions implemented

- Platform Owner is the only hardcoded account.
- Every other actor is generated from a local Test Scenario.
- A scenario requires only a Client name.
- A scenario can contain multiple Institutions.
- Creating an Institution requires only name + type.
- Newly created Institution becomes the active Institution.
- Scenario and Institution are global context selectors on every flow page.
- Actor can be switched globally: Platform Owner, Director, Admin, Teacher, Student, Parent, Principal, HOD, Staff.
- Actor switching reuses an existing token and automatically logs in only when a token is absent.
- Quick Login is available from the top context bar and has editable username/email and password fields.
- Role passwords are predictable test defaults: `Director@123`, `Admin@123`, `Teacher@123`, `Student@123`, `Parent@123`, `Principal@123`, `HOD@123`, `Staff@123`.
- ENV variables remain editable through the ENV / Debug drawer. Variables can be added or removed individually; Reset All remains available.
- Existing flow HTML/API step definitions are retained rather than duplicated into a new orchestration engine.
- Prepare Data creates local test context only.
- Bootstrap selection prepares a standard happy-path context and exposes the existing Platform Bootstrap flow for execution.
- Deleting a scenario deletes only local browser state. It never deletes backend data.

## Files

`shared.js` contains the scenario/context manager, quick login, token reuse, editable ENV store, and compatibility layer used by all flows.

`flow.css` contains the redesigned shell and responsive styling.

`index.html` is the scenario launcher.

`01_platform_owner.html` through `21_cross_institution.html` are the existing backend flow pages using the new shared shell.
