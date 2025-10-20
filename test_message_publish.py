#!/usr/bin/env python3
"""
Simple test to check if messages are being published to RabbitMQ
"""
import asyncio
import sys
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent
LIBS_DIR = PROJECT_ROOT / "libs"
COMMON_PY_DIR = LIBS_DIR / "common-py"

for p in (COMMON_PY_DIR, LIBS_DIR, PROJECT_ROOT):
    ps = str(p)
    if ps not in sys.path:
        sys.path.insert(0, ps)

from common_py.messaging import MessageBroker
from config import config

async def test_publish():
    """Test publishing a message"""
    print(f"Connecting to broker: {config.BUS_BROKER}")

    broker = MessageBroker(config.BUS_BROKER)
    await broker.connect()

    test_event = {
        "job_id": "test_debug_001",
        "event_id": "550e8400-e29b-41d4-a716-446655440999",
        "total_images": 1,
        "ready_images": [
            {
                "product_id": "PROD_TEST_001",
                "ready_path": "/data/tests/products/ready/test.jpg",
                "src": "test",
                "asin_or_itemid": "TEST001"
            }
        ]
    }

    print("Publishing test event to 'products.images.ready.batch'...")
    await broker.publish_event(
        topic="products.images.ready.batch",
        event_data=test_event,
        correlation_id="test_debug_001"
    )

    print("Event published successfully!")

    # Wait a bit
    await asyncio.sleep(2)

    await broker.disconnect()
    print("Disconnected")

if __name__ == "__main__":
    asyncio.run(test_publish())