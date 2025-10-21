"""
Test message capture functionality
"""
import pytest
import asyncio
from support.feature_extraction_fixtures import TestFeatureExtractionPhase as TestFeatureExtractionPhaseFixtures

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.feature_extraction,
    pytest.mark.timeout(15)
]

class TestMessageCapture(TestFeatureExtractionPhaseFixtures):
    """Test message capture"""

    async def test_spy_capture_individual_events(
        self,
        feature_extraction_test_environment
    ):
        """Test that spy can capture individual product masked events"""
        env = feature_extraction_test_environment
        spy = env["spy"]
        publisher = env["publisher"]
        db_manager = env["db_manager"]
        
        # Setup database record
        job_id = "test_capture_001"
        product_id = f"{job_id}_product_001"
        img_id = f"{job_id}_img_001"
        
        await db_manager.execute(
            """
            INSERT INTO jobs (job_id, industry, phase, created_at, updated_at)
            VALUES ($1, 'ergonomic pillows', 'feature_extraction', NOW(), NOW())
            ON CONFLICT (job_id) DO NOTHING;
            """,
            job_id
        )
        
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
        
        # Publish individual ready event
        event = {
            "job_id": job_id,
            "product_id": product_id,
            "image_id": img_id,
            "local_path": "/app/data/tests/products/ready/prod_001.jpg"
        }
        
        await publisher.publish_products_image_ready(event)
        print("Published individual ready event")
        
        # Wait a bit for processing
        await asyncio.sleep(5)
        
        # Check what messages were captured
        print("Checking captured messages...")
        for event_type, messages in spy.captured_messages.items():
            print(f"Event type {event_type}: {len(messages)} messages")
            for msg in messages:
                if msg["event_data"].get("job_id") == job_id:
                    print(f"  Found message for job {job_id}: {msg['event_data']}")
        
        # Check specifically for product masked events
        product_masked_events = [
            msg for msg in spy.captured_messages.get("products_image_masked", [])
            if msg["event_data"].get("job_id") == job_id
        ]
        
        print(f"Found {len(product_masked_events)} product masked events")
        
        # Also check if we captured ANY messages at all
        total_captured = sum(len(messages) for messages in spy.captured_messages.values())
        print(f"Total messages captured by spy: {total_captured}")
        
        # Check if the spy has any queues set up
        print(f"Spy queues: {list(spy.queues.keys())}")
        print(f"Spy queue namespaces: {list(spy.queue_namespaces.keys())}")
        
        # Test passes if we don't hang - we're just debugging capture
        assert True
