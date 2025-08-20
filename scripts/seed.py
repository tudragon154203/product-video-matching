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
from infra.config import config

logger = configure_logging("seed")

# Database connection
POSTGRES_DSN = config.POSTGRES_DSN


async def seed_database():
    """Seed database with sample data"""
    try:
        # Connect to database
        conn = await asyncpg.connect(POSTGRES_DSN)
        
        logger.info("Connected to database, starting seeding...")
        
        # Create sample job
        job_id = str(uuid.uuid4())
        await conn.execute(
            "INSERT INTO jobs (job_id, industry, phase) VALUES ($1, $2, $3)",
            job_id, "ergonomic pillows", "completed"
        )
        logger.info("Created sample job", job_id=job_id)
        
        # Create sample products (reduced by 90% - keep 1 out of 2)
        products = [
            {
                "id": str(uuid.uuid4()),
                "src": "amazon",
                "asin": "B08XYZ123",
                "title": "Ergonomic Memory Foam Pillow",
                "brand": "ComfortPlus",
                "url": "https://amazon.com/ergonomic-pillow-1"
            }
        ]
        
        for product in products:
            await conn.execute(
                "INSERT INTO products (product_id, src, asin_or_itemid, title, brand, url, job_id) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                product["id"], product["src"], product["asin"], product["title"],
                product["brand"], product["url"], job_id
            )
            
            # Create sample images for each product (reduced by 90% - keep 1 out of 2)
            for i in range(1):
                img_id = f"{product['id']}_img_{i}"
                await conn.execute(
                    "INSERT INTO product_images (img_id, product_id, local_path) VALUES ($1, $2, $3)",
                    img_id, product["id"], f"/app/data/products/{product['id']}/{img_id}.jpg"
                )
        
        logger.info("Created sample products", count=len(products))
        
        # Create sample videos (reduced by 90% - keep 1 out of 2)
        videos = [
            {
                "id": str(uuid.uuid4()),
                "platform": "youtube",
                "url": "https://youtube.com/watch?v=sample1",
                "title": "Best Ergonomic Pillows Review 2024",
                "duration": 180
            }
        ]
        
        for video in videos:
            await conn.execute(
                "INSERT INTO videos (video_id, platform, url, title, duration_s, job_id) VALUES ($1, $2, $3, $4, $5, $6)",
                video["id"], video["platform"], video["url"], video["title"],
                video["duration"], job_id
            )
            
            # Create sample frames for each video (reduced by 90% - keep 1 out of 3)
            for i in range(1):
                frame_id = f"{video['id']}_frame_{i}"
                timestamp = i * 30.0  # Every 30 seconds
                await conn.execute(
                    "INSERT INTO video_frames (frame_id, video_id, ts, local_path) VALUES ($1, $2, $3, $4)",
                    frame_id, video["id"], timestamp, f"/app/data/videos/{video['id']}/frames/{frame_id}.jpg"
                )
        
        logger.info("Created sample videos", count=len(videos))
        
        # Create sample matches (updated to reference remaining products and videos)
        match_id = str(uuid.uuid4())
        await conn.execute(
            """INSERT INTO matches (match_id, job_id, product_id, video_id, best_img_id, best_frame_id, ts, score)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
            match_id, job_id, products[0]["id"], videos[0]["id"],
            f"{products[0]['id']}_img_0", f"{videos[0]['id']}_frame_0", 30.0, 0.85
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