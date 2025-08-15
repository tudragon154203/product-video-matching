"""Add marketplace and price columns to products table (breaking change)

Revision ID: 004
Revises: 003
Create Date: 2025-08-15 15:37:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create marketplace enum type
    marketplace_enum = ENUM('us', 'de', 'au', name='marketplace_enum')
    marketplace_enum.create(op.get_bind())
    
    # Drop existing products table (breaking change)
    # First drop foreign key constraints from other tables
    op.drop_constraint('fk_matches_product_id', 'matches', type_='foreignkey')
    op.drop_constraint('fk_product_images_product_id', 'product_images', type_='foreignkey')
    
    # Drop indexes
    op.drop_index('idx_products_job_id', 'products')
    
    # Drop the products table
    op.drop_table('products')
    
    # Recreate products table with new columns
    op.create_table('products',
        sa.Column('product_id', sa.String(255), primary_key=True),
        sa.Column('src', sa.String(50), nullable=False),
        sa.Column('asin_or_itemid', sa.String(255), nullable=False),
        sa.Column('title', sa.Text()),
        sa.Column('brand', sa.String(255)),
        sa.Column('url', sa.Text()),
        sa.Column('marketplace', sa.Enum('us', 'de', 'au', name='marketplace_enum'), nullable=False),
        sa.Column('price', sa.String(100), nullable=True),  # String to store currency like "$20", "€3", "5 AUD"
        sa.Column('job_id', sa.String(255)),  # Keep existing job_id column
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # Recreate foreign key constraints
    op.create_foreign_key('fk_matches_product_id', 'matches', 'products', ['product_id'], ['product_id'])
    op.create_foreign_key('fk_product_images_product_id', 'product_images', 'products', ['product_id'], ['product_id'])
    
    # Recreate indexes
    op.create_index('idx_products_job_id', 'products', ['job_id'])


def downgrade() -> None:
    # This migration is a breaking change and cannot be safely rolled back
    # as it requires dropping and recreating the products table
    # which would lose all existing data
    pass