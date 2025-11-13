"""Add processed_events table for idempotency

Revision ID: 005
Revises: 004
Create Date: 2025-10-03
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create processed_events table for idempotency tracking
    op.create_table(
        'processed_events',
        sa.Column('event_id', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('event_id')
    )
    op.create_index('ix_processed_events_created_at', 'processed_events', ['created_at'])


def downgrade() -> None:
    # Drop processed_events table
    op.drop_index('ix_processed_events_created_at', table_name='processed_events')
    op.drop_table('processed_events')