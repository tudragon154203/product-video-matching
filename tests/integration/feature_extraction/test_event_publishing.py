"""
Test event publishing to debug pipeline issues
"""
import pytest
from support.feature_extraction_fixtures import TestFeatureExtractionPhase as TestFeatureExtractionPhaseFixtures

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.feature_extraction,
    pytest.mark.timeout(5)  # Very short timeout
]

class TestEventPublishing(TestFeatureExtractionPhaseFixtures):
    """Test event publishing"""

    async def test_publish_ready_event(
        self,
        feature_extraction_test_environment
    ):
        """Test that we can publish a ready event"""
        env = feature_extraction_test_environment
        publisher = env["publisher"]
        db_manager = env["db_manager"]
        
        # Setup simple database record
        job_id = "test_publish_001"
        await db_manager.execute(
            """
            INSERT INTO jobs (job_id, industry, phase, created_at, updated_at)
            VALUES ($1, 'ergonomic pillows', 'feature_extraction', NOW(), NOW())
            ON CONFLICT (job_id) DO NOTHING;
            """,
            job_id
        )
        
        # Publish a simple batch event
        event = {
            "job_id": job_id,
            "event_id": "test_event_001",
            "total_images": 1
        }
        
        await publisher.publish_products_images_ready_batch(event)
        print("Event published successfully")
        
        # Don't wait for any response - just verify publish worked
        assert True, "Event publishing completed without hanging"
