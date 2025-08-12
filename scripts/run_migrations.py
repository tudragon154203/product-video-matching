#!/usr/bin/env python3
"""
Run database migrations
"""
import sys
import os
import asyncio
sys.path.append('/tmp/libs')

# Add the project root to the path so we can import infra.config
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from common_py.database import DatabaseManager
from infra.config import config

async def run_migrations():
    """Run database migrations"""
    dsn = config.POSTGRES_DSN
    db = DatabaseManager(dsn)
    await db.connect()
    
    try:
        # Enable vector extension
        await db.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Create products table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id VARCHAR PRIMARY KEY,
                src VARCHAR NOT NULL,
                asin_or_itemid VARCHAR,
                title TEXT,
                brand VARCHAR,
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create product_images table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS product_images (
                img_id VARCHAR PRIMARY KEY,
                product_id VARCHAR REFERENCES products(product_id),
                local_path TEXT NOT NULL,
                emb_rgb vector(512),
                emb_gray vector(512),
                kp_blob_path TEXT,
                phash VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create videos table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                video_id VARCHAR PRIMARY KEY,
                platform VARCHAR NOT NULL,
                url TEXT NOT NULL,
                title TEXT,
                duration_s INTEGER,
                published_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create video_frames table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS video_frames (
                frame_id VARCHAR PRIMARY KEY,
                video_id VARCHAR REFERENCES videos(video_id),
                ts FLOAT NOT NULL,
                local_path TEXT NOT NULL,
                emb_rgb vector(512),
                emb_gray vector(512),
                kp_blob_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create matches table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                match_id VARCHAR PRIMARY KEY,
                job_id VARCHAR NOT NULL,
                product_id VARCHAR REFERENCES products(product_id),
                video_id VARCHAR REFERENCES videos(video_id),
                best_img_id VARCHAR,
                best_frame_id VARCHAR,
                ts FLOAT,
                score FLOAT NOT NULL,
                evidence_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create jobs table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id VARCHAR PRIMARY KEY,
                industry VARCHAR NOT NULL,
                status VARCHAR DEFAULT 'pending',
                progress FLOAT DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create indexes for better performance
        await db.execute("CREATE INDEX IF NOT EXISTS idx_product_images_product_id ON product_images(product_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_video_frames_video_id ON video_frames(video_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_matches_job_id ON matches(job_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_matches_score ON matches(score);")
        
        print("Database migrations completed successfully!")
        
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(run_migrations())