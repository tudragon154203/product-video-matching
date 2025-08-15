"""Add image_url_remote column to product_images table

Revision ID: 005
Revises: 004
Create Date: 2025-08-15 15:37:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add image_url_remote column to product_images table
    op.add_column('product_images', sa.Column('image_url_remote', sa.Text(), nullable=True))


def downgrade() -> None:
    # Drop image_url_remote column from product_images table
    op.drop_column('product_images', 'image_url_remote')