"""Add masked_local_path columns for product segmentation

Revision ID: 003
Revises: 002
Create Date: 2025-08-16
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add masked_local_path column to product_images table
    op.add_column('product_images', sa.Column('masked_local_path', sa.VARCHAR(500), nullable=True))
    
    # Add masked_local_path column to video_frames table
    op.add_column('video_frames', sa.Column('masked_local_path', sa.VARCHAR(500), nullable=True))
    
    # Add indexes for mask path queries (partial indexes for non-null values)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_product_images_masked_path 
        ON product_images(masked_local_path) 
        WHERE masked_local_path IS NOT NULL
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_video_frames_masked_path 
        ON video_frames(masked_local_path) 
        WHERE masked_local_path IS NOT NULL
    """)


def downgrade() -> None:
    # Drop indexes first
    op.execute("DROP INDEX IF EXISTS idx_product_images_masked_path")
    op.execute("DROP INDEX IF EXISTS idx_video_frames_masked_path")
    
    # Drop columns
    op.drop_column('product_images', 'masked_local_path')
    op.drop_column('video_frames', 'masked_local_path')