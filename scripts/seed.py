#!/usr/bin/env python3
"""
Database seeding script for development
"""
import asyncio
import asyncpg
import uuid
from datetime import datetime, timedelta
import os
import sys

# Add libs to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'libs'))

from common_py.logging_config import configure_logging

logger = configure_logging("seed")

# Database connection
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://postgres:dev@localhost:5432/postgres")


async def seed_database():
    """Seed database with sample data"""
    try:
        # Connect to database
        conn = await asyncpg.connect(POSTGRES_DSN)
        
        logger.info("Connected to database, starting seeding...")
        
        # Create sample job
        job_id = str(uuid.uuid4())
        await conn.execute(
            "INSERT INTO jobs (job_id, industry, status, phase) VALUES ($1, $2, $3, $4)",
            job_id, "ergonomic pillows", "completed", "completed"
        )
        logger.info("Created sample job", job_id=job_id)
        
        # Create sample products
        products = [
            {
                "id": str(uuid.uuid4()),
                "src": "amazon",
                "asin": "B08XYZ123",
                "title": "Ergonomic Memory Foam Pillow",
                "brand": "ComfortPlus",
                "url": "https://amazon.com/ergonomic-pillow-1"
            },
            {
                "id": str(uuid.uuid4()),
                "src": "ebay",
                "asin": "E789ABC456",
                "title": "Orthopedic Neck Support Pillow",
                "brand": "SleepWell",
                "url": "https://ebay.com/orthopedic-pillow-1"
            }
        ]
        
        for product in products:
            await conn.execute(
                "INSERT INTO products (product_id, src, asin_or_itemid, title, brand, url, job_id) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                product["id"], product["src"], product["asin"], product["title"], 
                product["brand"], product["url"], job_id
            )
            
            # Create sample images for each product
            for i in range(2):
                img_id = f"{product['id']}_img_{i}"
                await conn.execute(
                    "INSERT INTO product_images (img_id, product_id, local_path) VALUES ($1, $2, $3)",
                    img_id, product["id"], f"/app/data/products/{product['id']}/{img_id}.jpg"
                )
        
        logger.info("Created sample products", count=len(products))
        
        # Create sample videos
        videos = [
            {
                "id": str(uuid.uuid4()),
                "platform": "youtube",
                "url": "https://youtube.com/watch?v=sample1",
                "title": "Best Ergonomic Pillows Review 2024",
                "duration": 180
            },
            {
                "id": str(uuid.uuid4()),
                "platform": "youtube",
                "url": "https://youtube.com/watch?v=sample2",
                "title": "How to Choose the Right Pillow for Neck Pain",
                "duration": 240
            }
        ]
        
        for video in videos:
            await conn.execute(
                "INSERT INTO videos (video_id, platform, url, title, duration_s, job_id) VALUES ($1, $2, $3, $4, $5, $6)",
                video["id"], video["platform"], video["url"], video["title"], 
                video["duration"], job_id
            )
            
            # Create sample frames for each video
            for i in range(3):
                frame_id = f"{video['id']}_frame_{i}"
                timestamp = i * 30.0  # Every 30 seconds
                await conn.execute(
                    "INSERT INTO video_frames (frame_id, video_id, ts, local_path) VALUES ($1, $2, $3, $4)",
                    frame_id, video["id"], timestamp, f"/app/data/videos/{video['id']}/frames/{frame_id}.jpg"
                )
        
        logger.info("Created sample videos", count=len(videos))
        
        # Create sample matches
        match_id = str(uuid.uuid4())
        await conn.execute(
            """INSERT INTO matches (match_id, job_id, product_id, video_id, best_img_id, best_frame_id, ts, score) 
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
            match_id, job_id, products[0]["id"], videos[0]["id"], 
            f"{products[0]['id']}_img_0", f"{videos[0]['id']}_frame_1", 30.0, 0.85
        )
        
        logger.info("Created sample match", match_id=match_id)
        
        # Get final counts
        stats = {
            "jobs": await conn.fetchval("SELECT COUNT(*) FROM jobs"),
            "products": await conn.fetchval("SELECT COUNT(*) FROM products"),
            "product_images": await conn.fetchval("SELECT COUNT(*) FROM product_images"),
            "videos": await conn.fetchval("SELECT COUNT(*) FROM videos"),
            "video_frames": await conn.fetchval("SELECT COUNT(*) FROM video_frames"),
            "matches": await conn.fetchval("SELECT COUNT(*) FROM matches")
        }
        
        logger.info("Database seeding completed", stats=stats)
        
        await conn.close()
        
    except Exception as e:
        logger.error("Failed to seed database", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(seed_database())