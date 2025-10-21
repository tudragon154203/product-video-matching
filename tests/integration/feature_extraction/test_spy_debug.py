"""
Debug test for spy connection issues
"""
import pytest
from support.feature_extraction_spy import FeatureExtractionSpy

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.feature_extraction,
    pytest.mark.timeout(10)
]

class TestSpyDebug:
    """Debug test for spy connection"""

    async def test_spy_connection(self, message_broker):
        """Test spy connection setup"""
        print("Creating spy...")
        spy = FeatureExtractionSpy('amqp://guest:guest@localhost:5672//')
        
        print("Connecting spy...")
        await spy.connect()
        print("Spy connected successfully")
        
        print("Clearing messages...")
        spy.clear_messages()
        print("Messages cleared")
        
        print("Disconnecting spy...")
        await spy.disconnect()
        print("Spy disconnected successfully")
