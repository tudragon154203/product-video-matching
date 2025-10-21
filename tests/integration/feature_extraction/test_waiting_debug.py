"""
Test waiting behavior to debug timeout issues
"""
import pytest
from support.feature_extraction_fixtures import TestFeatureExtractionPhase as TestFeatureExtractionPhaseFixtures

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.feature_extraction,
    pytest.mark.timeout(10)
]

class TestWaitingDebug(TestFeatureExtractionPhaseFixtures):
    """Test waiting behavior"""

    async def test_wait_with_timeout(
        self,
        feature_extraction_test_environment
    ):
        """Test waiting with very short timeout"""
        env = feature_extraction_test_environment
        spy = env["spy"]
        publisher = env["publisher"]
        
        # Publish a simple batch event 
        job_id = "test_wait_001"
        event = {
            "job_id": job_id,
            "event_id": "test_event_001", 
            "total_images": 1
        }
        
        await publisher.publish_products_images_ready_batch(event)
        print("Event published")
        
        # Try to wait for response with very short timeout
        try:
            result = await spy.wait_for_products_images_masked(job_id, timeout=2)
            print(f"Got result: {result}")
        except TimeoutError as e:
            print(f"Expected timeout: {e}")
            # This is expected - we just want to see if the wait method works
        
        print("Wait test completed")
