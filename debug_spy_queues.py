#!/usr/bin/env python3
"""
Debug script to test spy queue bindings and message capture
"""
import asyncio
import sys
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent
TESTS_DIR = PROJECT_ROOT / "tests"
INTEGRATION_DIR = TESTS_DIR / "integration"

for p in (TESTS_DIR, INTEGRATION_DIR):
    ps = str(p)
    if ps not in sys.path:
        sys.path.insert(0, ps)

from support.feature_extraction_spy import FeatureExtractionSpy
from support.event_publisher import FeatureExtractionEventPublisher
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker

async def debug_spy_queues():
    """Debug spy queue setup and message capture"""
    
    # Setup database
    dsn = "postgres://postgres:dev@localhost:5444/product_video_matching"
    db_manager = DatabaseManager(dsn)
    await db_manager.connect()
    
    # Setup message broker for publishing
    broker = MessageBroker("amqp://guest:guest@localhost:5672//")
    await broker.connect()
    
    # Setup spy
    spy = FeatureExtractionSpy("amqp://guest:guest@localhost:5672//")
    await spy.connect()
    
    print(f"Spy queues created: {list(spy.queues.keys())}")
    print(f"Spy queue namespaces: {list(spy.queue_namespaces.keys())}")
    
    # Setup publisher
    publisher = FeatureExtractionEventPublisher(broker)
    
    # Clear any existing messages
    spy.clear_messages()
    
    # Setup test data
    job_id = "debug_spy_001"
    
    # Create job record
    await db_manager.execute(
        """
        INSERT INTO jobs (job_id, industry, phase, created_at, updated_at)
        VALUES ($1, 'ergonomic pillows', 'feature_extraction', NOW(), NOW())
        ON CONFLICT (job_id) DO NOTHING;
        """,
        job_id
    )
    
    # Create product record
    product_id = f"{job_id}_product_001"
    img_id = f"{job_id}_img_001"
    
    await db_manager.execute(
        """
        INSERT INTO products (product_id, job_id, src, asin_or_itemid, marketplace, created_at)
        VALUES ($1, $2, 'amazon', 'TEST001', 'us', NOW())
        ON CONFLICT (product_id) DO NOTHING;
        """,
        product_id, job_id
    )
    
    await db_manager.execute(
        """
        INSERT INTO product_images (img_id, product_id, local_path, created_at)
        VALUES ($1, $2, '/app/data/tests/products/ready/prod_001.jpg', NOW())
        ON CONFLICT (img_id) DO NOTHING;
        """,
        img_id, product_id
    )
    
    print("Database setup complete")
    
    # Publish a ready event
    event = {
        "job_id": job_id,
        "product_id": product_id,
        "image_id": img_id,
        "local_path": "/app/data/tests/products/ready/prod_001.jpg"
    }
    
    await publisher.publish_products_image_ready(event)
    print("Published ready event")
    
    # Wait for processing
    print("Waiting for processing...")
    await asyncio.sleep(10)
    
    # Check captured messages
    print("\n=== CAPTURED MESSAGES ===")
    total_captured = 0
    for event_type, messages in spy.captured_messages.items():
        count = len(messages)
        total_captured += count
        print(f"{event_type}: {count} messages")
        if count > 0:
            for i, msg in enumerate(messages):
                if msg["event_data"].get("job_id") == job_id:
                    print(f"  [{i}] {msg['event_data']}")
    
    print(f"\nTotal captured: {total_captured}")
    
    # Also manually publish a products.image.masked event to test direct capture
    print("\n=== TESTING DIRECT EVENT ===")
    masked_event = {
        "event_id": "debug_test_001",
        "job_id": job_id,
        "image_id": img_id,
        "mask_path": "/app/data/masks_product/test/debug.png"
    }
    
    await publisher.publish_event("products.image.masked", masked_event)
    print("Published direct masked event")
    
    await asyncio.sleep(2)
    
    # Check again for the direct event
    masked_messages = [
        msg for msg in spy.captured_messages.get("products_image_masked", [])
        if msg["event_data"].get("job_id") == job_id
    ]
    
    print(f"Found {len(masked_messages)} direct masked events")
    for msg in masked_messages:
        print(f"  {msg['event_data']}")
    
    # Cleanup
    await spy.disconnect()
    await broker.disconnect()
    await db_manager.disconnect()
    
    print("\nDebug complete")

if __name__ == "__main__":
    asyncio.run(debug_spy_queues())
