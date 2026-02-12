# VMS MVP Codex Rulebook (India)

---

## 1. Product Philosophy

This is an MVP for Indian veterinary clinics.

Optimize for:
- Single-clinic usage
- Low-tech users
- WhatsApp-first interactions
- UPI-first payments
- Manual override everywhere

If a feature increases friction, it is out of scope.

---

## 2. MVP Scope Lock

### Included

**Clinic**
- Role-based login (Admin, Vet, Staff)
- Pet medical records
- Appointment scheduling
- WhatsApp reminders
- Simple invoicing
- Inventory tracking
- Basic analytics
- Compliance data storage

**Pet Parent**
- Appointment booking
- Health record access
- Medication reminders
- UPI payments
- Secure record sharing

### Excluded (Phase 2+)

- Multi-clinic orgs
- AI diagnostics
- Insurance
- GST automation
- Telemedicine
- Marketplace
- Advanced analytics

Codex must refuse excluded features.

---

## 3. Architecture Guardrails

- Web-first frontend
- Modular monolith backend
- REST APIs
- Single relational DB
- Soft deletes only

---

## 4. Data Rules

- Every table must include `clinic_id`
- Audit fields mandatory
- No orphaned records

---

## 5. Access & Security

- RBAC only (admin, vet, staff)
- JWT auth
- OTP password reset
- HTTPS only

---

## 6. Scheduling Rules

- No overlapping vet appointments
- Configurable slot duration
- No calendar integrations

---

## 7. WhatsApp Rules

Mandatory for:
- Appointments
- Vaccinations
- Medication reminders
- Payments

All messages must be logged and retryable.

---

## 8. Billing & Payments

- Simple invoices
- Editable invoices
- UPI primary
- Manual mark-as-paid allowed

---

## 9. Inventory

- Name
- Quantity
- Expiry
- Low-stock threshold

No batch logic.

---

## 10. Analytics

- Appointments
- Revenue
- Top services
- Active pets

No real-time analytics.

---

## 11. Compliance

- Store registration numbers
- Store owner ID references
- No government integrations

---

## 12. Error Handling

- Never block core workflows
- Always allow override
- Log everything

---

## 13. Code Conventions

- Clear over clever
- Explicit enums
- No abbreviations

---

## 14. Codex Behavior

- Ask only blocking questions
- Implement minimal versions
- Do not refactor without permission

---

## 15. MVP Success Definition

- Clinic can run daily operations
- Staff needs no training
- ≥60% WhatsApp interactions
- Demoable end-to-end in 10 minutes
