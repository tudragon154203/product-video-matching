"""Remove published_at column from videos table

Revision ID: 004
Revises: 003
Create Date: 2025-08-18
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove published_at column from videos table
    op.drop_column('videos', 'published_at')


def downgrade() -> None:
    # Add published_at column back to videos table
    op.add_column('videos', sa.Column('published_at', sa.DateTime(), nullable=True))