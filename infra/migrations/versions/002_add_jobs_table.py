"""Add jobs table for orchestration

Revision ID: 002
Revises: 001
Create Date: 2024-12-08 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create jobs table
    op.create_table('jobs',
        sa.Column('job_id', sa.String(255), primary_key=True),
        sa.Column('industry', sa.String(255), nullable=False),
        sa.Column('phase', sa.String(50), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # Add job_id to products and videos tables for tracking
    op.add_column('products', sa.Column('job_id', sa.String(255)))
    op.add_column('videos', sa.Column('job_id', sa.String(255)))
    
    # Create indexes
    op.create_index('idx_products_job_id', 'products', ['job_id'])
    op.create_index('idx_videos_job_id', 'videos', ['job_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_products_job_id')
    op.drop_index('idx_videos_job_id')
    
    # Drop columns
    op.drop_column('products', 'job_id')
    op.drop_column('videos', 'job_id')
    
    # Drop table
    op.drop_table('jobs')