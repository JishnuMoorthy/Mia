# VMS MVP (Single Clinic)

Local-running MVP with simple admin UI and CRUD for clinics, users, pet parents, pets, appointments, medical records, inventory, invoices, payments, reminder logs, and message logs.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app
```

Open `http://127.0.0.1:8000`.

On first run, you will be prompted to create the clinic and the admin user. After that, use the login screen.

## One-command start (after setup)

```bash
python -m app
```

## Notes

- SQLite database file: `vms.db`
- You can override DB via `DATABASE_URL` (e.g., Postgres) as long as schema stays the same.

## Assumptions / deviations

- **Approved schema deviation**: Added `password_hash TEXT` to `users` for login (required for auth). No other schema changes.
- WhatsApp integration is **not implemented**. Only `reminder_logs` and `message_logs` are stored manually.
- JWT auth is used via an HTTP-only cookie for local use. OTP reset is a minimal phone-based reset (no external OTP service).
- HTTPS enforcement is not applied locally.

## CRUD Coverage

- Clinics (create/view/edit/delete)
- Users (admin/vet/staff) + login
- Pet Parents (CRUD)
- Pets (CRUD linked to Pet Parent)
- Appointments (CRUD; overlap check for same vet/date/time)
- Medical Records (CRUD linked to Pet + Vet)
- Inventory Items (CRUD)
- Invoices (CRUD; status flow draft → issued → paid/cancelled)
- Payments (CRUD; status pending/paid/failed)
- Reminder Logs + Message Logs (CRUD-like create + list)
