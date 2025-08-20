"""Initial schema (translated from 01-init.sql)

Revision ID: 001
Revises: None
Create Date: 2025-08-16
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extensions & settings
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    # NOTE: ALTER DATABASE requires superuser; keep it to mirror the .sql
    op.execute("ALTER DATABASE product_video_matching SET timezone TO 'Asia/Ho_Chi_Minh';")
    op.execute("SET TIME ZONE 'Asia/Ho_Chi_Minh';")

    # Types (create enum if not exists)
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'marketplace_enum') THEN
            CREATE TYPE marketplace_enum AS ENUM ('us', 'de', 'au');
          END IF;
        END$$;
        """
    )

    # Fresh create: drop old tables in dependency order (safe if first run)
    op.execute("DROP TABLE IF EXISTS matches        CASCADE;")
    op.execute("DROP TABLE IF EXISTS product_images CASCADE;")
    op.execute("DROP TABLE IF EXISTS video_frames   CASCADE;")
    op.execute("DROP TABLE IF EXISTS videos         CASCADE;")
    op.execute("DROP TABLE IF EXISTS products       CASCADE;")
    op.execute("DROP TABLE IF EXISTS jobs           CASCADE;")
    op.execute("DROP TABLE IF EXISTS phase_events   CASCADE;")

    # Tables
    op.execute(
        """
        CREATE TABLE products (
          product_id        VARCHAR(255) PRIMARY KEY,
          src               VARCHAR(50)  NOT NULL,
          asin_or_itemid    VARCHAR(255) NOT NULL,
          title             TEXT,
          brand             VARCHAR(255),
          url               TEXT,
          marketplace       marketplace_enum NOT NULL,
          price             VARCHAR(100),
          job_id            VARCHAR(255),
          created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    op.execute(
        """
        CREATE TABLE product_images (
          img_id            VARCHAR(255) PRIMARY KEY,
          product_id        VARCHAR(255) REFERENCES products(product_id),
          local_path        VARCHAR(500) NOT NULL,
          kp_blob_path      VARCHAR(500),
          phash             BIGINT,
          image_url_remote  TEXT,
          emb_rgb           vector(512),
          emb_gray          vector(512),
          created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    op.execute(
        """
        CREATE TABLE videos (
          video_id          VARCHAR(255) PRIMARY KEY,
          platform          VARCHAR(50) NOT NULL,
          url               TEXT NOT NULL,
          title             TEXT,
          duration_s        INTEGER,
          published_at      TIMESTAMP,
          job_id            VARCHAR(255),
          created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    op.execute(
        """
        CREATE TABLE video_frames (
          frame_id          VARCHAR(255) PRIMARY KEY,
          video_id          VARCHAR(255) REFERENCES videos(video_id),
          ts                FLOAT NOT NULL,
          local_path        VARCHAR(500) NOT NULL,
          kp_blob_path      VARCHAR(500),
          emb_rgb           vector(512),
          emb_gray          vector(512),
          created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    op.execute(
        """
        CREATE TABLE matches (
          match_id          VARCHAR(255) PRIMARY KEY,
          job_id            VARCHAR(255) NOT NULL,
          product_id        VARCHAR(255) REFERENCES products(product_id),
          video_id          VARCHAR(255) REFERENCES videos(video_id),
          best_img_id       VARCHAR(255) REFERENCES product_images(img_id),
          best_frame_id     VARCHAR(255) REFERENCES video_frames(frame_id),
          ts                FLOAT,
          score             FLOAT NOT NULL,
          evidence_path     VARCHAR(500),
          created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    op.execute(
        """
        CREATE TABLE jobs (
          job_id            VARCHAR(255) PRIMARY KEY,
          industry          VARCHAR(255) NOT NULL,
          phase             VARCHAR(50)  NOT NULL DEFAULT 'collection',
          query             TEXT,
          queries           JSONB,
          created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    op.execute(
        """
        CREATE TABLE phase_events (
          event_id          VARCHAR(255) PRIMARY KEY,
          job_id            VARCHAR(255) NOT NULL,
          name              VARCHAR(100) NOT NULL,
          received_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # Indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_products_job_id               ON products(job_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_product_images_product_id     ON product_images(product_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_videos_job_id                 ON videos(job_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_video_frames_video_id         ON video_frames(video_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_matches_job_id                ON matches(job_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_matches_score                 ON matches(score);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created_at               ON jobs (created_at DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_phase_events_job_id           ON phase_events(job_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_phase_events_name             ON phase_events(name);")

    # Vector HNSW indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_product_images_emb_rgb  ON product_images USING hnsw (emb_rgb  vector_cosine_ops);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_product_images_emb_gray ON product_images USING hnsw (emb_gray vector_cosine_ops);")


def downgrade() -> None:
    # Drop vector indexes first
    op.execute("DROP INDEX IF EXISTS idx_product_images_emb_rgb;")
    op.execute("DROP INDEX IF EXISTS idx_product_images_emb_gray;")

    # Drop secondary indexes
    op.execute("DROP INDEX IF EXISTS idx_products_job_id;")
    op.execute("DROP INDEX IF EXISTS idx_product_images_product_id;")
    op.execute("DROP INDEX IF EXISTS idx_videos_job_id;")
    op.execute("DROP INDEX IF EXISTS idx_video_frames_video_id;")
    op.execute("DROP INDEX IF EXISTS idx_matches_job_id;")
    op.execute("DROP INDEX IF EXISTS idx_matches_score;")
    op.execute("DROP INDEX IF EXISTS idx_jobs_created_at;")
    op.execute("DROP INDEX IF EXISTS idx_phase_events_job_id;")
    op.execute("DROP INDEX IF EXISTS idx_phase_events_name;")

    # Drop tables (reverse order)
    op.execute("DROP TABLE IF EXISTS phase_events;")
    op.execute("DROP TABLE IF EXISTS jobs;")
    op.execute("DROP TABLE IF EXISTS matches;")
    op.execute("DROP TABLE IF EXISTS video_frames;")
    op.execute("DROP TABLE IF EXISTS videos;")
    op.execute("DROP TABLE IF EXISTS product_images;")
    op.execute("DROP TABLE IF EXISTS products;")

    # Optionally drop enum and extension
    op.execute("DROP TYPE IF EXISTS marketplace_enum;")
    op.execute("DROP EXTENSION IF EXISTS vector;")
