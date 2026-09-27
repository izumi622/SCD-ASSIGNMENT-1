"""001_initial_schema

Revision ID: 001_initial
Revises: 
Create Date: 2026-09-27 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use dialect-aware UUID type
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        uuid_col = postgresql.UUID(as_uuid=True)
        server_default_uuid = sa.text("gen_random_uuid()")
    else:
        uuid_col = sa.CHAR(36)
        server_default_uuid = None

    op.create_table(
        'complaints',
        sa.Column('id', uuid_col, primary_key=True, server_default=server_default_uuid),
        sa.Column('text', sa.String(length=2000), nullable=False),
        sa.Column('location', sa.String(length=200), nullable=False),
        sa.Column('reporter_contact', sa.String(length=255), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='open'),
        sa.Column('ai_summary', sa.String(length=140), nullable=True),
        sa.Column('triaged_by', sa.String(length=64), nullable=False),
        sa.Column('triage_latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('length(text) >= 10', name='chk_complaint_text_min_length'),
        sa.CheckConstraint('length(text) <= 2000', name='chk_complaint_text_max_length'),
        sa.CheckConstraint('length(location) >= 3', name='chk_complaint_location_min_length'),
        sa.CheckConstraint('length(location) <= 200', name='chk_complaint_location_max_length'),
    )

    # Required Indexes:
    # 1. Compound index on (status, priority) for filtered dashboard views
    op.create_index('ix_complaints_status_priority', 'complaints', ['status', 'priority'], unique=False)
    # 2. Index on created_at for chronologically paginated complaint listings
    op.create_index('ix_complaints_created_at', 'complaints', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_complaints_created_at', table_name='complaints')
    op.drop_index('ix_complaints_status_priority', table_name='complaints')
    op.drop_table('complaints')
