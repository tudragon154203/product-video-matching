#!/usr/bin/env python3
"""
Debug script to test event publishing and validation
"""
import asyncio
import sys
import json
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent
TESTS_DIR = PROJECT_ROOT / "tests"
INTEGRATION_DIR = TESTS_DIR / "integration"

for p in (TESTS_DIR, INTEGRATION_DIR):
    ps = str(p)
    if ps not in sys.path:
        sys.path.insert(0, ps)

from support.event_publisher import FeatureExtractionEventPublisher
from support.test_data import build_product_image_records, build_products_image_ready_event
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker

async def debug_event_publish():
    """Debug event publishing"""
    
    # Setup database
    dsn = "postgres://postgres:dev@localhost:5444/product_video_matching"
    db_manager = DatabaseManager(dsn)
    await db_manager.connect()
    
    # Setup message broker
    broker = MessageBroker("amqp://guest:guest@localhost:5672//")
    await broker.connect()
    
    # Setup publisher
    publisher = FeatureExtractionEventPublisher(broker)
    
    # Create test data
    job_id = "debug_event_001"
    product_records = build_product_image_records(job_id, 1)
    
    print("=== PRODUCT RECORDS ===")
    for record in product_records:
        print(json.dumps(record, indent=2))
    
    # Create individual events
    individual_events = [
        build_products_image_ready_event(job_id, record)
        for record in product_records
    ]
    
    print("\n=== INDIVIDUAL EVENTS ===")
    for event in individual_events:
        print(json.dumps(event, indent=2))
    
    # Setup database
    await db_manager.execute(
        """
        INSERT INTO jobs (job_id, industry, phase, created_at, updated_at)
        VALUES ($1, 'ergonomic pillows', 'feature_extraction', NOW(), NOW())
        ON CONFLICT (job_id) DO NOTHING;
        """,
        job_id
    )
    
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
    
    print("Database setup complete")
    
    # Publish events
    for event in individual_events:
        print(f"\nPublishing event: {event['image_id']}")
        await publisher.publish_products_image_ready(event)
        await asyncio.sleep(0.1)
    
    print("\nWaiting for processing...")
    await asyncio.sleep(5)
    
    # Cleanup
    await broker.disconnect()
    await db_manager.disconnect()
    
    print("\nDebug complete")

if __name__ == "__main__":
    asyncio.run(debug_event_publish())
