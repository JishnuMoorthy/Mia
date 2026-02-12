"""initial

Revision ID: 0001_initial
Revises: 
Create Date: 2026-02-04 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clinics",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("phone", sa.Text(), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("city", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("pincode", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("clinic_id", sa.String(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("phone", sa.String(), nullable=False, unique=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("role", sa.Enum("admin", "vet", "staff", name="user_role", native_enum=False), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "pet_parents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("clinic_id", sa.String(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("phone", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("govt_id_reference", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "pets",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("clinic_id", sa.String(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("pet_parent_id", sa.String(), sa.ForeignKey("pet_parents.id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("species", sa.Text(), nullable=False),
        sa.Column("breed", sa.Text(), nullable=True),
        sa.Column("gender", sa.Enum("male", "female", "unknown", name="pet_gender", native_enum=False), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("registration_number", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "appointments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("clinic_id", sa.String(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("pet_id", sa.String(), sa.ForeignKey("pets.id"), nullable=False),
        sa.Column("vet_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("appointment_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("status", sa.Enum("scheduled", "completed", "cancelled", "no_show", name="appointment_status", native_enum=False), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "medical_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("clinic_id", sa.String(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("pet_id", sa.String(), sa.ForeignKey("pets.id"), nullable=False),
        sa.Column("vet_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("visit_date", sa.Date(), nullable=False),
        sa.Column("symptoms", sa.Text(), nullable=True),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        sa.Column("prescription", sa.Text(), nullable=True),
        sa.Column("follow_up_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "invoices",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("clinic_id", sa.String(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("pet_id", sa.String(), sa.ForeignKey("pets.id"), nullable=False),
        sa.Column("invoice_number", sa.Text(), nullable=False),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("gst_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.Enum("draft", "issued", "paid", "cancelled", name="invoice_status", native_enum=False), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("clinic_id", sa.String(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("invoice_id", sa.String(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("payment_method", sa.Enum("upi", "cash", "card", name="payment_method", native_enum=False), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.Enum("pending", "paid", "failed", name="payment_status", native_enum=False), nullable=False),
        sa.Column("reference_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "inventory_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("clinic_id", sa.String(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("low_stock_threshold", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "reminder_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("clinic_id", sa.String(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("entity_type", sa.Enum("appointment", "medication", "vaccination", "payment", name="reminder_entity_type", native_enum=False), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("channel", sa.Enum("whatsapp", name="reminder_channel", native_enum=False), nullable=False),
        sa.Column("status", sa.Enum("sent", "failed", name="reminder_status", native_enum=False), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "message_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("clinic_id", sa.String(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("recipient_phone", sa.Text(), nullable=False),
        sa.Column("template_name", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.Enum("queued", "sent", "failed", name="message_status", native_enum=False), nullable=False),
        sa.Column("provider_message_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("message_logs")
    op.drop_table("reminder_logs")
    op.drop_table("inventory_items")
    op.drop_table("payments")
    op.drop_table("invoices")
    op.drop_table("medical_records")
    op.drop_table("appointments")
    op.drop_table("pets")
    op.drop_table("pet_parents")
    op.drop_table("users")
    op.drop_table("clinics")
