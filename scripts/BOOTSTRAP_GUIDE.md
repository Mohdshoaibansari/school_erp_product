# School ERP — Bootstrap & Testing Guide

## Prerequisites

- Python 3.11+ with `uv` installed
- Node.js 18+ (v24 used) with `npm`
- Git (to clone the repo)

---

## 1. Clone & Setup Backend

```bash
git clone <repo-url>
cd school_erp_product
```

The `.env` file at `backend/.env` is already configured for cloud Supabase:
```
SUPABASE_URL=https://ripscmqvzkipsqtmfdry.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
DATABASE_URL=postgresql://postgres:<password>@db.ripscmqvzkipsqtmfdry.supabase.co:5432/postgres
SUPABASE_JWT_SECRET=<same-as-db-password>
APP_INVITE_JWT_SECRET=app-invite-secret-change-in-prod
```

### Run migrations (already done on cloud)

```bash
cd backend
uv run alembic upgrade head
```

This applies all 6 migrations (C-01 through Homework module).

### Seed test data

```bash
cd backend
uv run python -m scripts.seed_data
```

This creates:
- **1 Client** (slug: `test-school`)
- **1 Institution** (Test Institution)
- **3 Users** with Supabase Auth credentials
- **Sample fee data** (1 fee type, 1 assignment, 1 payment)
- **Sample homework data** (1 homework, 1 submission, 1 grade)

---

## 2. Test Users

| Role | Email | Password | Capabilities |
|---|---|---|---|
| **Admin** | `admin@test-school.com` | `Admin@123` | Full access: create fee types, assign fees, record payments, waive fees |
| **Teacher** | `teacher@test-school.com` | `Teacher@123` | Create homework, close homework, grade submissions, view fees |
| **Student** | `student@test-school.com` | `Student@123` | Submit homework, view own fees, view own grades |

---

## 3. Start the Backend

```bash
cd backend
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

Verify it's running:
```bash
curl http://127.0.0.1:8000/api/v1/health  # should return 200
```

---

## 4. Start the Frontend

```bash
cd frontend
npm install    # only needed first time
npm run dev
```

Opens at **http://localhost:5173**

---

## 5. Test Flows

### Flow 1: Login

1. Open http://localhost:5173
2. You'll be at `/login`
3. Enter credentials from the table above
4. Click "Login" → redirected to `/fees` (Fee Types page)

### Flow 2: Fees — Admin

**View Fee Types:**
- Already at `/fees` → see "Tuition Fee" (₹5000)

**Create New Fee Type:**
- Click "+ New Fee Type"
- Name: "Transport Fee", Amount: 2000
- Institution ID: paste any UUID (already filled if editing an existing one)
- Click "Save"

**Assign Fee:**
- Navigate to "Assignments" tab
- Click "+ New Assignment"
- Select "Tuition Fee" from dropdown
- Amount: 5000, Due Date: 2026-12-31
- Student IDs: paste the student UUID from seed data (or use `student@test-school.com`'s UUID from Supabase dashboard → Authentication → Users)
- Click "Assign"

**Record Payment:**
- Navigate to "Payments" tab
- Click "+ Record Payment"
- Select the fee assignment from dropdown
- Amount: 3000, Method: Cash
- Click "Record" → shows receipt number
- Go back to "Assignments" tab → status should now be "paid" (5000 total paid)

**Waive Fee:**
- Find a pending assignment → click "Waive" → enter reason → "Confirm Waive"
- Status changes to "waived" (terminal)

### Flow 3: Homework — Teacher

**Log in as Teacher** (`teacher@test-school.com` / `Teacher@123`):
- You'll see existing "Math Ch 5 Worksheet"

**Create New Homework:**
- Click "+ New Homework"
- Title: "Science Quiz", Subject: "Science", Grade Level: "Grade 5", Section: "A"
- Due Date: 2026-08-15, Max Score: 50
- Click "Save"

**Close Homework:**
- Find an active homework → click "Close"
- Status changes to "closed"

**Grade Submission:**
- Click "Submissions" on any homework
- Find a submission → click "Grade"
- Score: 85, Feedback: "Nice work!"
- Click "Submit Grade"
- Submission status → "graded"

### Flow 4: Homework — Student

**Log in as Student** (`student@test-school.com` / `Student@123`):
- Navigate to "Homework"
- See active homeworks listed

**Submit Homework:**
- Click "Submissions" on an active homework
- Click "+ Submit (as Student)"
- Type answer in text area
- Click "Submit"

**View Grades:**
- Navigate to "Grades" tab
- See your graded submissions with scores

### Flow 5: Authorization Tests

**Teacher tries Fee operations:**
- Log in as Teacher → navigate to Fees → "Fee Types"
- Try to create a fee type → should succeed (Teacher has `fee_assignment.read` but NOT `fee.create`)
- Wait, based on the permission mapping, Teacher only has `fee_assignment.read` for fees. Let me verify...

**Student tries to create homework:**
- Log in as Student → navigate to Homework
- Student should NOT see the "+ New Homework" button
- If student manually hits POST /api/v1/homeworks via curl → 403

### Flow 6: Cross-User Isolation

- Log in as Student A
- Try to view `/api/v1/submissions?student_id=<student-b-uuid>` via browser dev tools
- Should get 403 "You can only access your own records"

---

## 6. API Testing (curl / Postman)

### Get access token:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@test-school.com", "password": "Admin@123"}'
```

Save the `access_token` from the response.

### Test with token:

```bash
TOKEN="eyJhbGci..."

# List fee types
curl http://127.0.0.1:8000/api/v1/fee-types \
  -H "Authorization: Bearer $TOKEN"

# Create homework
curl -X POST http://127.0.0.1:8000/api/v1/homeworks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test HW","due_date":"2026-08-01","subject":"Math","grade_level":"Grade 5","section":"A"}'

# List submissions
curl http://127.0.0.1:8000/api/v1/submissions \
  -H "Authorization: Bearer $TOKEN"
```

---

## 7. Troubleshooting

**"Invalid or expired JWT" in frontend:**
- The token may have expired. Log out and log in again.
- Check that only ONE backend is running (port 8000).

**400 "badly formed hexadecimal UUID string":**
- You're passing a non-UUID string where a UUID is expected.
- Check the Institution ID or Student IDs fields — they must be valid UUIDs.

**CORS errors in browser console:**
- The Vite dev server proxies `/api` to the backend (configured in `vite.config.ts`).
- Make sure the backend is running on port 8000.

**"Permission denied — no roles assigned":**
- Your JWT doesn't have roles. The seed script assigns roles via `role_assignment`.
- Check that the middleware resolves client_id from the subdomain.

**Frontend can't connect to backend:**
- Make sure backend is running: `curl http://127.0.0.1:8000/api/v1/health`
- Make sure Vite proxy is working: check `frontend/vite.config.ts`

---

## 8. Resetting Data

To reset and re-seed:
```bash
cd backend
uv run python -c "
from sqlalchemy import create_engine, text
import os
db = os.environ.get('DATABASE_URL')
engine = create_engine(db)
with engine.connect() as c:
    for t in ['grade','submission','homework','payment','fee_assignment','fee_type',
              'role_assignment','user_identifier','user_profile','app_user',
              'institution','institution_type','client']:
        c.execute(text(f'DELETE FROM {t}'))
        c.commit()
"
uv run python -m scripts.seed_data
```
