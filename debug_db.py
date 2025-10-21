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

async def debug_db():
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
        # Check for recent test jobs
        result = await db_manager.fetch_all(
            "SELECT job_id, industry, phase, created_at FROM jobs WHERE job_id LIKE 'test_%' ORDER BY created_at DESC LIMIT 5"
        )
        print("Recent test jobs:")
        for row in result:
            print(f"  {row}")
        
        # Check for products in test jobs
        result = await db_manager.fetch_all(
            "SELECT product_id, job_id, src, asin_or_itemid FROM products WHERE job_id LIKE 'test_%' LIMIT 10"
        )
        print("\nTest products:")
        for row in result:
            print(f"  {row}")
        
        # Check for product images
        result = await db_manager.fetch_all(
            "SELECT img_id, product_id, local_path FROM product_images WHERE product_id LIKE 'test_%' LIMIT 10"
        )
        print("\nTest product images:")
        for row in result:
            print(f"  {row}")
            
    finally:
        await db_manager.disconnect()

if __name__ == "__main__":
    asyncio.run(debug_db())
