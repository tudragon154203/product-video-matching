"""Initial schema with pgvector support

Revision ID: 001
Revises: 
Create Date: 2024-12-08 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create products table
    op.create_table('products',
        sa.Column('product_id', sa.String(255), primary_key=True),
        sa.Column('src', sa.String(50), nullable=False),
        sa.Column('asin_or_itemid', sa.String(255), nullable=False),
        sa.Column('title', sa.Text()),
        sa.Column('brand', sa.String(255)),
        sa.Column('url', sa.Text()),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # Create product_images table with vector columns
    op.create_table('product_images',
        sa.Column('img_id', sa.String(255), primary_key=True),
        sa.Column('product_id', sa.String(255), sa.ForeignKey('products.product_id')),
        sa.Column('local_path', sa.String(500), nullable=False),
        sa.Column('kp_blob_path', sa.String(500)),
        sa.Column('phash', sa.BigInteger()),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # Add vector columns using raw SQL (pgvector specific)
    op.execute('ALTER TABLE product_images ADD COLUMN emb_rgb vector(512)')
    op.execute('ALTER TABLE product_images ADD COLUMN emb_gray vector(512)')
    
    # Create videos table
    op.create_table('videos',
        sa.Column('video_id', sa.String(255), primary_key=True),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('title', sa.Text()),
        sa.Column('duration_s', sa.Integer()),
        sa.Column('published_at', sa.TIMESTAMP()),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # Create video_frames table with vector columns
    op.create_table('video_frames',
        sa.Column('frame_id', sa.String(255), primary_key=True),
        sa.Column('video_id', sa.String(255), sa.ForeignKey('videos.video_id')),
        sa.Column('ts', sa.Float(), nullable=False),
        sa.Column('local_path', sa.String(500), nullable=False),
        sa.Column('kp_blob_path', sa.String(500)),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # Add vector columns using raw SQL (pgvector specific)
    op.execute('ALTER TABLE video_frames ADD COLUMN emb_rgb vector(512)')
    op.execute('ALTER TABLE video_frames ADD COLUMN emb_gray vector(512)')
    
    # Create matches table
    op.create_table('matches',
        sa.Column('match_id', sa.String(255), primary_key=True),
        sa.Column('job_id', sa.String(255), nullable=False),
        sa.Column('product_id', sa.String(255), sa.ForeignKey('products.product_id')),
        sa.Column('video_id', sa.String(255), sa.ForeignKey('videos.video_id')),
        sa.Column('best_img_id', sa.String(255), sa.ForeignKey('product_images.img_id')),
        sa.Column('best_frame_id', sa.String(255), sa.ForeignKey('video_frames.frame_id')),
        sa.Column('ts', sa.Float()),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('evidence_path', sa.String(500)),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # Create indexes for performance
    op.create_index('idx_matches_job_id', 'matches', ['job_id'])
    op.create_index('idx_matches_score', 'matches', ['score'])
    op.create_index('idx_product_images_product_id', 'product_images', ['product_id'])
    op.create_index('idx_video_frames_video_id', 'video_frames', ['video_id'])
    
    # Create HNSW indexes for vector similarity search
    op.execute('CREATE INDEX idx_product_images_emb_rgb ON product_images USING hnsw (emb_rgb vector_cosine_ops)')
    op.execute('CREATE INDEX idx_product_images_emb_gray ON product_images USING hnsw (emb_gray vector_cosine_ops)')


def downgrade() -> None:
    # Drop indexes first
    op.execute('DROP INDEX IF EXISTS idx_product_images_emb_rgb')
    op.execute('DROP INDEX IF EXISTS idx_product_images_emb_gray')
    op.drop_index('idx_matches_job_id')
    op.drop_index('idx_matches_score')
    op.drop_index('idx_product_images_product_id')
    op.drop_index('idx_video_frames_video_id')
    
    # Drop tables
    op.drop_table('matches')
    op.drop_table('video_frames')
    op.drop_table('videos')
    op.drop_table('product_images')
    op.drop_table('products')
    
    # Drop extension
    op.execute('DROP EXTENSION IF EXISTS vector')