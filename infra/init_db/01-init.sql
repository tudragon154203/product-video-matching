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


-- Tables
CREATE TABLE IF NOT EXISTS products (
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

CREATE TABLE IF NOT EXISTS product_images (
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

CREATE TABLE IF NOT EXISTS videos (
  video_id          VARCHAR(255) PRIMARY KEY,
  platform          VARCHAR(50) NOT NULL,
  url               TEXT NOT NULL,
  title             TEXT,
  duration_s        INTEGER,
  published_at      TIMESTAMP,
  created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS job_videos (
  job_id            VARCHAR(255) NOT NULL,
  video_id          VARCHAR(255) NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
  platform          VARCHAR(50) NOT NULL,
  assigned_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (job_id, video_id)
);

CREATE TABLE IF NOT EXISTS video_frames (
  frame_id          VARCHAR(255) PRIMARY KEY,
  video_id          VARCHAR(255) REFERENCES videos(video_id),
  ts                FLOAT NOT NULL,
  local_path        VARCHAR(500) NOT NULL,
  kp_blob_path      VARCHAR(500),
  emb_rgb           vector(512),
  emb_gray          vector(512),
  created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS matches (
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

CREATE TABLE IF NOT EXISTS jobs (
  job_id            VARCHAR(255) PRIMARY KEY,
  industry          VARCHAR(255) NOT NULL,
  phase             VARCHAR(50)  NOT NULL DEFAULT 'collection',
  query             TEXT,
  queries           JSONB,
  created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS phase_events (
  event_id          VARCHAR(255) PRIMARY KEY,
  job_id            VARCHAR(255) NOT NULL,
  name              VARCHAR(100) NOT NULL,
  received_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_products_job_id               ON products(job_id);
CREATE INDEX IF NOT EXISTS idx_product_images_product_id     ON product_images(product_id);
CREATE INDEX IF NOT EXISTS idx_video_frames_video_id         ON video_frames(video_id);
CREATE INDEX IF NOT EXISTS idx_matches_job_id                ON matches(job_id);
CREATE INDEX IF NOT EXISTS idx_matches_score                 ON matches(score);
CREATE INDEX IF NOT EXISTS idx_job_videos_video_id           ON job_videos(video_id);
CREATE INDEX IF NOT EXISTS idx_job_videos_job_platform       ON job_videos(job_id, platform);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at               ON jobs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_phase_events_job_id           ON phase_events(job_id);
CREATE INDEX IF NOT EXISTS idx_phase_events_name             ON phase_events(name);

-- Vector HNSW indexes
CREATE INDEX IF NOT EXISTS idx_product_images_emb_rgb  ON product_images USING hnsw (emb_rgb  vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_product_images_emb_gray ON product_images USING hnsw (emb_gray vector_cosine_ops);

COMMIT;  -- <== Bổ sung dòng này
