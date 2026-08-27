# AGENTS.md

Guidance for AI coding assistants working in this repository.

## Project Overview

**Bhavesh Solanki RTO & Insurance Advisor CRM** — a full-stack, single-admin CRM for managing RTO (Regional Transport Office) & Insurance advisory operations across four service categories: **Insurance**, **Permit**, **Fitness/PUC**, **License**.

Key features: single-admin enforcement, JWT login, dashboard analytics (summary cards + Recharts monthly collection chart), master customer form, category-filtered views, 30-day expiry detection, WhatsApp reminder sending with audit log (`MessageLog`), payment recording with printable A4 PDF receipts, and a daily expiry-scan cron job.

> **NOTE:** `README.md` and `PRD/TRD` docs are partially **stale** — they describe an old `crm_app` with an OTP login flow and Puppeteer receipts. The current implementation uses modular Django apps, direct JWT login (no OTP), and ReportLab PDFs. Trust the code over the docs.

## Repository Layout

```
backend/          Django 5 + DRF API (MySQL)
  config/         Project settings, root URLs, WSGI/ASGI
  accounts/       Single admin user + JWT auth endpoints
  customers/      Customer CRUD + category-specific serializers
  payments/       Payment recording + PDF receipt generation (ReportLab)
  reminders/      WhatsApp reminder provider + MessageLog + cron scan command
  dashboard/      Summary + monthly-collection analytics endpoints
  common/         Shared permissions, pagination, exception handler, throttles
  _e2e_test.py    Standalone end-to-end test script (no pytest suite)
frontend/         React 19 + Vite + Tailwind v4 SPA
  src/pages/      Route-level pages (Dashboard, Customers, CategoryPage, AddCustomer, Receipts, Login, Signup)
  src/components/ Navbar, CustomerForm (modal)
  src/context/    AuthContext (auth state)
  src/services/   api.js (axios instance)
```

## Tech Stack

- **Backend:** Django 5.2, Django REST Framework, MySQL (`mysqlclient`), `djangorestframework-simplejwt` (JWT), `django-cors-headers`, `django-filter`, `drf-spectacular` (Swagger), `reportlab` (PDFs), `django-crontab`
- **Frontend:** React 19, Vite 8, Tailwind CSS v4, React Router v7, React Hook Form, React Hot Toast, Recharts, Axios
- **Linting:** `oxlint` (frontend). No automated test suite exists for either side.

## Backend Conventions

- **No trailing slashes on API URLs** (`APPEND_SLASH = False`). Routes are defined manually (see `customers/urls.py`) rather than via DRF routers, precisely to match the frontend's slash-less convention. Never add a router-based URL that appends a slash.
- **Response envelope** — every endpoint returns `{ success: bool, message?, data? }`. Errors are normalized by `common/exceptions.py` to `{ success: false, message: "...", errors: {...} }` (message flattened to a single human-readable string). New endpoints must follow this shape.
- **Auth:** custom `Admin` model (`accounts/models.py`, UUID pk). Enforce exactly one admin via `Admin.save()` and `AdminManager.exists_already()`. Signup returns 403 once an admin exists. All business endpoints use `common.permissions.IsTheOneAdmin` (functionally `IsAuthenticated`).
- **Decimal/amounts:** `amount_total`, `amount_paid`, `amount_pending` are `DecimalField`s. In JSON they must be serialized as **strings** (DRF does this automatically). `Customer.amount_paid` is a **cached, derived value** — never accept it as writable input; always recompute via `customer.recompute_amount_paid()` after any Payment create/update/delete.
- **Categories:** primary `category` field (choices: `insurance`, `permit`, `fitness_puc`, `license`) plus a `categories` JSON list. `customers/filters.py` filters `categories__icontains=f'"{value}"'` since JSON contains isn't portable.
- **Category pages:** server-side field filtering is done by swapping in a category-specific serializer for the `list` action only (`CATEGORY_SERIALIZERS` in `customers/serializers.py`). Keep category page data-minimal; the `fitness_puc` and `license` pages expose only a small allowlist.
- **Pagination:** `common/pagination.StandardResultsSetPagination` (page size 20, max 10000). The frontend requests `page_size=10000` to load the full register.
- **No cache:** customer responses set `Cache-Control: no-store` headers (see `CustomerViewSet.finalize_response`).
- **WhatsApp reminders:** `reminders/services.py` defines a `WhatsAppProvider` ABC with `StubWhatsAppProvider` (default, logs to console) and `MetaCloudAPIProvider` (enabled when `WHATSAPP_API_TOKEN` + `WHATSAPP_PHONE_NUMBER_ID` are set). `send_reminder()` **always** writes a `MessageLog` row (sent or failed) and returns `(log, success)`.
- **Cron:** `scan_expiring_customers` management command flags customers whose `end_date` is within 30 days. `django-crontab` only works on Linux (`manage.py crontab add`); on Windows schedule `python manage.py scan_expiring_customers` via Task Scheduler instead.

## Frontend Conventions

- **API layer:** `src/services/api.js` exports a configured axios instance. JWT is kept **in memory only** (never localStorage/sessionStorage) — a page refresh ends the session. A 401 response clears the token and redirects to `/login`.
- **Auth state:** `AuthContext` holds `admin`, `token`, `refreshToken`. Consume via `useAuth()`; wrap protected routes with `<ProtectedRoute>` (see `App.jsx`).
- **Forms:** React Hook Form + `react-hot-toast` for feedback. Error messages come from `err.response?.data?.message`.
- **Category pages** are a single `CategoryPage` component driven by a `category` prop with routes `/insurance`, `/permit`, `/fitness-puc`, `/license`.
- **Customer form** (`components/CustomerForm.jsx`): on create, an optional "amount paid" is posted as a separate `/payments` record after the customer is created; on edit the paid amount is editable and any change is reconciled against the Payment records via `PUT /receipts/{id}/amount` (which creates/shrinks Payments so `amount_paid` stays consistent).
- **Styling:** Tailwind v4 classes plus existing CSS utility classes (`btn`, `btn-primary`, `btn-ghost`, `btn-danger`, `btn-sm`, `card`, `badge-*`, `form-control`, `form-label`, `spinner`, `modal-*`, `table-wrapper`, `empty-state`). Keep using these rather than inventing new ones.

## Commands

Backend (workdir `backend/`):
- Install: `python -m venv venv` then `pip install -r requirements.txt`
- Run: `python manage.py runserver 0.0.0.0:5000` (frontend expects port 5000)
- Migrations: `python manage.py makemigrations && python manage.py migrate`
- Verify: `python manage.py check`
- Expiry scan: `python manage.py scan_expiring_customers`

Frontend (workdir `frontend/`):
- Install: `npm install`
- Dev: `npm run dev` (Vite on port 5173, proxies `/api` → backend)
- Lint: `npm run lint` (oxlint) — run after frontend changes
- Build: `npm run build`

## Gotchas

- `frontend/.env` sets `VITE_API_URL=http://localhost:8004/api`, which overrides the default `/api` proxy → backend `:5000`. If the backend isn't running on 8004, the app fails to reach the API; update `.env` to match your backend port.
- Backend `.env` and `venv/`, frontend `node_modules/` and `dist/` are gitignored; `.env` files are present locally but should not be committed.
- JWT tokens come from `LoginView` as `access`/`refresh`/`token`; the frontend uses `res.data.access` and `res.data.user`.
- Leftover/scratch files exist and are not wired up: `accounts/views_new.py`, `accounts/views.py.new`, `accounts/services.py` (empty), `backend/_e2e_test.py`, `backend/_test_server.log`. Don't import from them.
- Do not add code comments beyond what's needed — but the existing codebase is heavily commented with decision rationale; preserve that style when extending.
