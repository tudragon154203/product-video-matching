CREATE EXTENSION IF NOT EXISTS vector;

-- Create products table
CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(255) PRIMARY KEY,
    src VARCHAR(50) NOT NULL,
    asin_or_itemid VARCHAR(255) NOT NULL,
    title TEXT,
    brand VARCHAR(255),
    url TEXT,
    job_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create product_images table
CREATE TABLE IF NOT EXISTS product_images (
    img_id VARCHAR(255) PRIMARY KEY,
    product_id VARCHAR(255) REFERENCES products(product_id),
    local_path VARCHAR(500) NOT NULL,
    kp_blob_path VARCHAR(500),
    phash BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add vector columns
ALTER TABLE product_images ADD COLUMN IF NOT EXISTS emb_rgb vector(512);
ALTER TABLE product_images ADD COLUMN IF NOT EXISTS emb_gray vector(512);

-- Create videos table
CREATE TABLE IF NOT EXISTS videos (
    video_id VARCHAR(255) PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    url TEXT NOT NULL,
    title TEXT,
    duration_s INTEGER,
    published_at TIMESTAMP,
    job_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create video_frames table
CREATE TABLE IF NOT EXISTS video_frames (
    frame_id VARCHAR(255) PRIMARY KEY,
    video_id VARCHAR(255) REFERENCES videos(video_id),
    ts FLOAT NOT NULL,
    local_path VARCHAR(500) NOT NULL,
    kp_blob_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add vector columns
ALTER TABLE video_frames ADD COLUMN IF NOT EXISTS emb_rgb vector(512);
ALTER TABLE video_frames ADD COLUMN IF NOT EXISTS emb_gray vector(512);

-- Create matches table
CREATE TABLE IF NOT EXISTS matches (
    match_id VARCHAR(255) PRIMARY KEY,
    job_id VARCHAR(255) NOT NULL,
    product_id VARCHAR(255) REFERENCES products(product_id),
    video_id VARCHAR(255) REFERENCES videos(video_id),
    best_img_id VARCHAR(255) REFERENCES product_images(img_id),
    best_frame_id VARCHAR(255) REFERENCES video_frames(frame_id),
    ts FLOAT,
    score FLOAT NOT NULL,
    evidence_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create jobs table
CREATE TABLE IF NOT EXISTS jobs (
    job_id VARCHAR(255) PRIMARY KEY,
    industry VARCHAR(255) NOT NULL,
    phase VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_matches_job_id ON matches(job_id);
CREATE INDEX IF NOT EXISTS idx_matches_score ON matches(score);
CREATE INDEX IF NOT EXISTS idx_product_images_product_id ON product_images(product_id);
CREATE INDEX IF NOT EXISTS idx_video_frames_video_id ON video_frames(video_id);
CREATE INDEX IF NOT EXISTS idx_products_job_id ON products(job_id);
CREATE INDEX IF NOT EXISTS idx_videos_job_id ON videos(job_id);

-- Create HNSW indexes for vector similarity search
CREATE INDEX IF NOT EXISTS idx_product_images_emb_rgb ON product_images USING hnsw (emb_rgb vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_product_images_emb_gray ON product_images USING hnsw (emb_gray vector_cosine_ops);