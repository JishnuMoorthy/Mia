from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import Column, Date, DateTime, Enum as SAEnum, JSON, Numeric, String, Time
from sqlmodel import Field, SQLModel


def uuid_str() -> str:
    return str(uuid.uuid4())


class UserRole(str, Enum):
    admin = "admin"
    vet = "vet"
    staff = "staff"


class PetGender(str, Enum):
    male = "male"
    female = "female"
    unknown = "unknown"


class AppointmentStatus(str, Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"


class InvoiceStatus(str, Enum):
    draft = "draft"
    issued = "issued"
    paid = "paid"
    cancelled = "cancelled"


class PaymentMethod(str, Enum):
    upi = "upi"
    cash = "cash"
    card = "card"


class PaymentStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"


class ReminderEntityType(str, Enum):
    appointment = "appointment"
    medication = "medication"
    vaccination = "vaccination"
    payment = "payment"


class ReminderChannel(str, Enum):
    whatsapp = "whatsapp"


class ReminderStatus(str, Enum):
    sent = "sent"
    failed = "failed"


class MessageStatus(str, Enum):
    queued = "queued"
    sent = "sent"
    failed = "failed"


class Clinic(SQLModel, table=True):
    __tablename__ = "clinics"

    id: str = Field(default_factory=uuid_str, primary_key=True)
    name: str
    phone: str
    address: str
    city: str
    state: str
    pincode: str
    created_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, sa_column=Column(DateTime))
    updated_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, sa_column=Column(DateTime))
    deleted_at: Optional[dt.datetime] = Field(default=None, sa_column=Column(DateTime))


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(default_factory=uuid_str, primary_key=True)
    clinic_id: str = Field(index=True, foreign_key="clinics.id")
    name: str
    phone: str = Field(sa_column=Column(String, unique=True))
    email: Optional[str] = None
    role: UserRole = Field(sa_column=Column(SAEnum(UserRole, name="user_role", native_enum=False)))
    is_active: bool = True
    password_hash: str
    created_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, sa_column=Column(DateTime))
    updated_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, sa_column=Column(DateTime))
    deleted_at: Optional[dt.datetime] = Field(default=None, sa_column=Column(DateTime))


class PetParent(SQLModel, table=True):
    __tablename__ = "pet_parents"

    id: str = Field(default_factory=uuid_str, primary_key=True)
    clinic_id: str = Field(index=True, foreign_key="clinics.id")
    name: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    govt_id_reference: Optional[str] = None
    created_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, sa_column=Column(DateTime))
    updated_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, sa_column=Column(DateTime))
    deleted_at: Optional[dt.datetime] = Field(default=None, sa_column=Column(DateTime))


class Pet(SQLModel, table=True):
    __tablename__ = "pets"

    id: str = Field(default_factory=uuid_str, primary_key=True)
    clinic_id: str = Field(index=True, foreign_key="clinics.id")
    pet_parent_id: str = Field(index=True, foreign_key="pet_parents.id")
    name: str
    species: str
    breed: Optional[str] = None
    gender: PetGender = Field(sa_column=Column(SAEnum(PetGender, name="pet_gender", native_enum=False)))
    date_of_birth: Optional[dt.date] = Field(default=None, sa_column=Column(Date))
    registration_number: Optional[str] = None
    sterilization_status: Optional[str] = None
    alerts: Optional[str] = None
    created_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, sa_column=Column(DateTime))
    updated_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, sa_column=Column(DateTime))
    deleted_at: Optional[dt.datetime] = Field(default=None, sa_column=Column(DateTime))


class Appointment(SQLModel, table=True):
    __tablename__ = "appointments"

    id: str = Field(default_factory=uuid_str, primary_key=True)
    clinic_id: str = Field(index=True, foreign_key="clinics.id")
    pet_id: str = Field(index=True, foreign_key="pets.id")
    vet_id: str = Field(index=True, foreign_key="users.id")
    appointment_date: dt.date = Field(sa_column=Column(Date))
    start_time: dt.time = Field(sa_column=Column(Time))
    end_time: dt.time = Field(sa_column=Column(Time))
    status: AppointmentStatus = Field(sa_column=Column(SAEnum(AppointmentStatus, name="appointment_status", native_enum=False)))
    notes: Optional[str] = None
    procedure_type: Optional[str] = None
    created_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, sa_column=Column(DateTime))
    updated_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, sa_column=Column(DateTime))
    deleted_at: Optional[dt.datetime] = Field(default=None, sa_column=Column(DateTime))


class MedicalRecord(SQLModel, table=True):
    __tablename__ = "medical_records"

    id: str = Field(default_factory=uuid_str, primary_key=True)
    clinic_id: str = Field(index=True, foreign_key="clinics.id")
    pet_id: str = Field(index=True, foreign_key="pets.id")
    vet_id: str = Field(index=True, foreign_key="users.id")
    visit_date: dt.date = Field(sa_column=Column(Date))
    symptoms: Optional[str] = None
    diagnosis: Optional[str] = None
    prescription: Optional[str] = None
    follow_up_date: Optional[dt.date] = Field(default=None, sa_column=Column(Date))
    created_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, sa_column=Column(DateTime))
    updated_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, sa_column=Column(DateTime))
    deleted_at: Optional[dt.datetime] = Field(default=None, sa_column=Column(DateTime))


class Invoice(SQLModel, table=True):
    __tablename__ = "invoices"

    id: str = Field(default_factory=uuid_str, primary_key=True)
    clinic_id: str = Field(index=True, foreign_key="clinics.id")
    pet_id: str = Field(index=True, foreign_key="pets.id")
    invoice_number: str
    total_amount: Decimal = Field(sa_column=Column(Numeric(10, 2)))
    gst_amount: Decimal = Field(sa_column=Column(Numeric(10, 2)))
    status: InvoiceStatus = Field(sa_column=Column(SAEnum(InvoiceStatus, name="invoice_status", native_enum=False)))
    created_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, sa_column=Column(DateTime))
    updated_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, sa_column=Column(DateTime))
    deleted_at: Optional[dt.datetime] = Field(default=None, sa_column=Column(DateTime))


class Payment(SQLModel, table=True):
    __tablename__ = "payments"

    id: str = Field(default_factory=uuid_str, primary_key=True)
    clinic_id: str = Field(index=True, foreign_key="clinics.id")
    invoice_id: str = Field(index=True, foreign_key="invoices.id")
    payment_method: PaymentMethod = Field(sa_column=Column(SAEnum(PaymentMethod, name="payment_method", native_enum=False)))
    amount: Decimal = Field(sa_column=Column(Numeric(10, 2)))
    status: PaymentStatus = Field(sa_column=Column(SAEnum(PaymentStatus, name="payment_status", native_enum=False)))
    reference_id: Optional[str] = None
    created_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, sa_column=Column(DateTime))
    updated_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, sa_column=Column(DateTime))
    deleted_at: Optional[dt.datetime] = Field(default=None, sa_column=Column(DateTime))


class InventoryItem(SQLModel, table=True):
    __tablename__ = "inventory_items"

    id: str = Field(default_factory=uuid_str, primary_key=True)
    clinic_id: str = Field(index=True, foreign_key="clinics.id")
    name: str
    quantity: int
    expiry_date: Optional[dt.date] = Field(default=None, sa_column=Column(Date))
    low_stock_threshold: int
    created_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, sa_column=Column(DateTime))
    updated_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, sa_column=Column(DateTime))
    deleted_at: Optional[dt.datetime] = Field(default=None, sa_column=Column(DateTime))


class ReminderLog(SQLModel, table=True):
    __tablename__ = "reminder_logs"

    id: str = Field(default_factory=uuid_str, primary_key=True)
    clinic_id: str = Field(index=True, foreign_key="clinics.id")
    entity_type: ReminderEntityType = Field(sa_column=Column(SAEnum(ReminderEntityType, name="reminder_entity_type", native_enum=False)))
    entity_id: str
    channel: ReminderChannel = Field(sa_column=Column(SAEnum(ReminderChannel, name="reminder_channel", native_enum=False)))
    status: ReminderStatus = Field(sa_column=Column(SAEnum(ReminderStatus, name="reminder_status", native_enum=False)))
    failure_reason: Optional[str] = None
    sent_at: Optional[dt.datetime] = Field(default=None, sa_column=Column(DateTime))
    created_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, sa_column=Column(DateTime))


class MessageLog(SQLModel, table=True):
    __tablename__ = "message_logs"

    id: str = Field(default_factory=uuid_str, primary_key=True)
    clinic_id: str = Field(index=True, foreign_key="clinics.id")
    recipient_phone: str
    template_name: str
    payload: dict = Field(sa_column=Column(JSON))
    status: MessageStatus = Field(sa_column=Column(SAEnum(MessageStatus, name="message_status", native_enum=False)))
    provider_message_id: Optional[str] = None
    created_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, sa_column=Column(DateTime))
