"""
Test the new wait_for_products_image_masked method
"""
import pytest
from support.feature_extraction_spy import FeatureExtractionSpy

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.feature_extraction,
    pytest.mark.timeout(10)
]

class TestNewMethod:
    """Test new spy method"""

    async def test_new_method_exists(self, message_broker):
        """Test that the new method exists"""
        spy = FeatureExtractionSpy('amqp://guest:guest@localhost:5672//')
        
        # Check if the method exists
        assert hasattr(spy, 'wait_for_products_image_masked'), "Method should exist"
        assert callable(getattr(spy, 'wait_for_products_image_masked')), "Method should be callable"
        
        await spy.connect()
        await spy.disconnect()
        
        print("New method exists and is callable")
