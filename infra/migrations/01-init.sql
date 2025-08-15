-- init.sql (compressed & cleaned)

BEGIN;

-- Extensions & settings
CREATE EXTENSION IF NOT EXISTS vector;
ALTER DATABASE product_video_matching SET timezone TO 'Asia/Ho_Chi_Minh';
SET TIME ZONE 'Asia/Ho_Chi_Minh';

-- Types
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'marketplace_enum') THEN
    CREATE TYPE marketplace_enum AS ENUM ('us', 'de', 'au');
  END IF;
END$$;

-- Fresh create (drop in dependency order if rerun)
DROP TABLE IF EXISTS matches        CASCADE;
DROP TABLE IF EXISTS product_images CASCADE;
DROP TABLE IF EXISTS video_frames   CASCADE;
DROP TABLE IF EXISTS videos         CASCADE;
DROP TABLE IF EXISTS products       CASCADE;
DROP TABLE IF EXISTS jobs           CASCADE;
DROP TABLE IF EXISTS phase_events   CASCADE;

-- Tables
CREATE TABLE products (
  product_id        VARCHAR(255) PRIMARY KEY,
  src               VARCHAR(50)  NOT NULL,
  asin_or_itemid    VARCHAR(255) NOT NULL,
  title             TEXT,
  brand             VARCHAR(255),
  url               TEXT,
  marketplace       marketplace_enum NOT NULL,
  price             VARCHAR(100),            -- "$20", "€3", "5 AUD"
  job_id            VARCHAR(255),
  created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE product_images (
  img_id            VARCHAR(255) PRIMARY KEY,
  product_id        VARCHAR(255) REFERENCES products(product_id),
  local_path        VARCHAR(500) NOT NULL,
  kp_blob_path      VARCHAR(500),
  phash             BIGINT,
  image_url_remote  TEXT,                    -- original remote URL
  emb_rgb           vector(512),
  emb_gray          vector(512),
  created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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

CREATE TABLE jobs (
  job_id            VARCHAR(255) PRIMARY KEY,
  industry          VARCHAR(255) NOT NULL,
  phase             VARCHAR(50)  NOT NULL DEFAULT 'collection',
  query             TEXT,
  queries           JSONB,
  created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE phase_events (
  event_id          VARCHAR(255) PRIMARY KEY,
  job_id            VARCHAR(255) NOT NULL,
  name              VARCHAR(100) NOT NULL,
  received_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_products_job_id               ON products(job_id);
CREATE INDEX IF NOT EXISTS idx_product_images_product_id     ON product_images(product_id);
CREATE INDEX IF NOT EXISTS idx_videos_job_id                 ON videos(job_id);
CREATE INDEX IF NOT EXISTS idx_video_frames_video_id         ON video_frames(video_id);
CREATE INDEX IF NOT EXISTS idx_matches_job_id                ON matches(job_id);
CREATE INDEX IF NOT EXISTS idx_matches_score                 ON matches(score);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at               ON jobs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_phase_events_job_id           ON phase_events(job_id);
CREATE INDEX IF NOT EXISTS idx_phase_events_name             ON phase_events(name);

-- Vector HNSW indexes
CREATE INDEX IF NOT EXISTS idx_product_images_emb_rgb  ON product_images USING hnsw (emb_rgb  vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_product_images_emb_gray ON product_images USING hnsw (emb_gray vector_cosine_ops);

COMMIT;
