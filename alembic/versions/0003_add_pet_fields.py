"""add sterilization_status and alerts to pets

Revision ID: 0003_add_pet_fields
Revises: 0002_add_procedure_type
Create Date: 2026-02-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_add_pet_fields"
down_revision = "0002_add_procedure_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pets", sa.Column("sterilization_status", sa.String(), nullable=True))
    op.add_column("pets", sa.Column("alerts", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("pets", "alerts")
    op.drop_column("pets", "sterilization_status")
