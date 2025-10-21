#!/usr/bin/env python3
import asyncio
import os
import sys
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent
LIBS_DIR = PROJECT_ROOT / "libs"
COMMON_PY_DIR = LIBS_DIR / "common-py"
TESTS_DIR = PROJECT_ROOT / "tests"

for p in (COMMON_PY_DIR, LIBS_DIR, PROJECT_ROOT, TESTS_DIR):
    ps = str(p)
    if ps not in sys.path:
        sys.path.insert(0, ps)

from common_py.database import DatabaseManager

async def test_simple_db_setup():
    # Set environment for test database
    os.environ.update({
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5444",
        "POSTGRES_DB": "product_video_matching",
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "dev",
    })
    
    dsn = f"postgres://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
    db_manager = DatabaseManager(dsn)
    await db_manager.connect()
    
    try:
        # Test data
        job_id = "test_simple_001"
        product_records = [
            {
                "product_id": f"{job_id}_product_001",
                "img_id": f"{job_id}_img_001", 
                "local_path": "/app/data/tests/products/ready/prod_001.jpg",
                "src": "amazon",
                "asin_or_itemid": f"{job_id}_ASIN_001",
                "marketplace": "us",
            }
        ]
        
        # Create job record
        await db_manager.execute(
            """
            INSERT INTO jobs (job_id, industry, phase, created_at, updated_at)
            VALUES ($1, 'ergonomic pillows', 'feature_extraction', NOW(), NOW())
            ON CONFLICT (job_id) DO NOTHING;
            """,
            job_id
        )
        print(f"Created job: {job_id}")

        # Insert product records
        for record in product_records:
            await db_manager.execute(
                """
                INSERT INTO products (product_id, job_id, src, asin_or_itemid, marketplace, created_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (product_id) DO NOTHING;
                """,
                record["product_id"],
                job_id,
                record["src"],
                record["asin_or_itemid"],
                record["marketplace"],
            )

            await db_manager.execute(
                """
                INSERT INTO product_images (img_id, product_id, local_path, created_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (img_id) DO NOTHING;
                """,
                record["img_id"],
                record["product_id"],
                record["local_path"],
            )
        
        print("Created product and image records")
        
        # Verify data was inserted
        result = await db_manager.fetch_all(
            "SELECT product_id, job_id, src FROM products WHERE job_id = $1",
            job_id
        )
        print(f"Found {len(result)} products:")
        for row in result:
            print(f"  {row}")
            
        result = await db_manager.fetch_all(
            "SELECT img_id, product_id, local_path FROM product_images WHERE product_id LIKE $1",
            f"{job_id}%"
        )
        print(f"Found {len(result)} images:")
        for row in result:
            print(f"  {row}")
            
    finally:
        await db_manager.disconnect()

if __name__ == "__main__":
    asyncio.run(test_simple_db_setup())
