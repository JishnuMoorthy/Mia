# DATABASE_SCHEMA_INSTRUCTIONS_V0 — VMS MVP

---

## Global Rules

1. Every table MUST include `clinic_id`
2. Soft deletes only (`deleted_at`)
3. UUID primary keys
4. Explicit enums only
5. No extra tables or fields

---

## clinics

```sql
id UUID PK
name TEXT
phone TEXT
address TEXT
city TEXT
state TEXT
pincode TEXT
created_at TIMESTAMP
updated_at TIMESTAMP
deleted_at TIMESTAMP

Users

id UUID PK
clinic_id UUID FK
name TEXT
phone TEXT UNIQUE
email TEXT
role ENUM('admin','vet','staff')
is_active BOOLEAN
created_at TIMESTAMP
updated_at TIMESTAMP
deleted_at TIMESTAMP


pet_parents

id UUID PK
clinic_id UUID FK
name TEXT
phone TEXT
email TEXT
address TEXT
govt_id_reference TEXT
created_at TIMESTAMP
updated_at TIMESTAMP
deleted_at TIMESTAMP

Pets

id UUID PK
clinic_id UUID FK
pet_parent_id UUID FK
name TEXT
species TEXT
breed TEXT
gender ENUM('male','female','unknown')
date_of_birth DATE
registration_number TEXT
created_at TIMESTAMP
updated_at TIMESTAMP
deleted_at TIMESTAMP

Appointments

id UUID PK
clinic_id UUID FK
pet_id UUID FK
vet_id UUID FK
appointment_date DATE
start_time TIME
end_time TIME
status ENUM('scheduled','completed','cancelled','no_show')
notes TEXT
created_at TIMESTAMP
updated_at TIMESTAMP
deleted_at TIMESTAMP

Medical Records

id UUID PK
clinic_id UUID FK
pet_id UUID FK
vet_id UUID FK
visit_date DATE
symptoms TEXT
diagnosis TEXT
prescription TEXT
follow_up_date DATE
created_at TIMESTAMP
updated_at TIMESTAMP
deleted_at TIMESTAMP

Invoices

id UUID PK
clinic_id UUID FK
pet_id UUID FK
invoice_number TEXT
total_amount DECIMAL
gst_amount DECIMAL
status ENUM('draft','issued','paid','cancelled')
created_at TIMESTAMP
updated_at TIMESTAMP
deleted_at TIMESTAMP


Payments

id UUID PK
clinic_id UUID FK
invoice_id UUID FK
payment_method ENUM('upi','cash','card')
amount DECIMAL
status ENUM('pending','paid','failed')
reference_id TEXT
created_at TIMESTAMP
updated_at TIMESTAMP
deleted_at TIMESTAMP


Inventory Items

id UUID PK
clinic_id UUID FK
name TEXT
quantity INTEGER
expiry_date DATE
low_stock_threshold INTEGER
created_at TIMESTAMP
updated_at TIMESTAMP
deleted_at TIMESTAMP


Reminder_logs

id UUID PK
clinic_id UUID FK
entity_type ENUM('appointment','medication','vaccination','payment')
entity_id UUID
channel ENUM('whatsapp')
status ENUM('sent','failed')
failure_reason TEXT
sent_at TIMESTAMP
created_at TIMESTAMP


Message_logs

id UUID PK
clinic_id UUID FK
recipient_phone TEXT
template_name TEXT
payload JSON
status ENUM('queued','sent','failed')
provider_message_id TEXT
created_at TIMESTAMP


Final Instruction
Implement exactly as defined.
Do not add fields or tables.
If unclear, stop and ask.