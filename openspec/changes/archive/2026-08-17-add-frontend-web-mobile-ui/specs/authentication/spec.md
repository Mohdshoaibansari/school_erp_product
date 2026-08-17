# Spec Delta — Authentication (ADDED frontend UI)

> **Change:** add-frontend-web-mobile-ui
> **Domain:** authentication
> **Impact:** ADDED (net-new frontend auth UI)
> **Source:** `docs/architecture/adr-frontend-implementation.md` (D5, R2, R3), `docs/prd/frontend-web-mobile.md` (P1-AC-6..P1-AC-12)

---

## ADDED Requirements

### REQ-FE-AUTH-01: Login

The app SHALL provide a login screen where a user enters email and password. On success, a JWT SHALL be issued and the app shell SHALL load with the user's role-filtered navigation. On failure, the app SHALL show an inline error with no route change (P1-AC-6).

#### Scenario: Successful login
- **WHEN** a user submits valid email + password
- **THEN** the app issues a JWT and loads the app shell with role-filtered navigation

#### Scenario: Failed login
- **WHEN** a user submits invalid credentials
- **THEN** the app shows an inline error and does not change route

---

### REQ-FE-AUTH-02: Account Activation

The app SHALL provide an activation screen reachable from an activation invite link. A user SHALL confirm their account (setting/confirming credentials as required). On activation, the user SHALL land on the login screen (R3, P1-AC-7).

#### Scenario: Activation completes to login
- **WHEN** a user completes account activation via an invite link
- **THEN** the user is redirected to the login screen (R3)

---

### REQ-FE-AUTH-03: OTP Flow

The app SHALL support request-and-verify OTP flows for activation and password reset only (no login 2FA step-up in this build). A user SHALL be able to request an OTP, receive it out-of-band, enter it, and verify it to proceed. A wrong or expired OTP SHALL show an inline error and allow re-request (R2, P1-AC-8).

#### Scenario: OTP request and verify
- **WHEN** a user triggers an OTP-protected action (activation or password reset)
- **THEN** the app lets them request, enter, and verify an OTP to proceed

#### Scenario: Wrong or expired OTP
- **WHEN** a user enters a wrong or expired OTP
- **THEN** the app shows an inline error and allows re-request

#### Scenario: No login 2FA step-up
- **WHEN** a user logs in
- **THEN** no OTP step-up is shown (OTP is activation + password reset only, R2)

---

### REQ-FE-AUTH-04: Password Reset

The app SHALL provide a "Forgot password" flow: a user requests a reset, receives a reset link/code, opens the reset screen, sets a new password, and confirms. On completion, the user SHALL be redirected to login with a success state (P1-AC-9).

#### Scenario: Complete password reset
- **WHEN** a user completes the forgot-password → reset → new-password flow
- **THEN** the app redirects to login with a success state

---

### REQ-FE-AUTH-05: Password Change (Logged In)

A logged-in user SHALL be able to change their password from profile/settings by entering current and new passwords and confirming. On success, the app SHALL confirm the change and keep the session valid (or re-auth per policy) (P1-AC-10).

#### Scenario: Change password while logged in
- **WHEN** a logged-in user submits current + new password with confirmation
- **THEN** the app confirms the change and the session remains valid (or re-auths per policy)

---

### REQ-FE-AUTH-06: Logout

A logged-in user SHALL be able to log out, after which the session SHALL be terminated and the user SHALL be returned to the login screen (P1-AC-11).

#### Scenario: Log out
- **WHEN** a user selects "Log out"
- **THEN** the session is terminated and the user is returned to login

---

### REQ-FE-AUTH-07: Silent Token Refresh

While a session is active, the app SHALL refresh the access token silently. If a refresh fails with 401, the app SHALL return the user to login (P1-AC-4).

#### Scenario: Silent refresh succeeds
- **WHEN** the access token nears expiry during an active session
- **THEN** the app refreshes it silently without interrupting the user

#### Scenario: Silent refresh fails
- **WHEN** a silent refresh returns 401
- **THEN** the app returns the user to login

---

### REQ-FE-AUTH-08: Auth Screens Responsive and Themed

All auth screens SHALL be responsive and match the "Minimalist Modern" design system (primary `#0052FF`, Inter/Calistoga, semantic colors) (P1-AC-12, D9).

#### Scenario: Auth screens match design system
- **WHEN** any auth screen renders on desktop or mobile
- **THEN** it is responsive and matches the Minimalist Modern Mantine theme
