"""Remove redundant status column from jobs table

Revision ID: 003
Revises: 002
Create Date: 2024-12-08 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the status column from jobs table
    op.drop_column('jobs', 'status')
    
    # Drop the index on status column
    op.drop_index('idx_jobs_status', table_name='jobs')


def downgrade() -> None:
    # Add the status column back to jobs table
    op.add_column('jobs', sa.Column('status', sa.String(50), nullable=False, server_default='running'))
    
    # Create index on status column
    op.create_index('idx_jobs_status', 'jobs', ['status'])