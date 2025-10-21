"""
Debug test for observability validator issues
"""
import pytest
from support.observability_validator import ObservabilityValidator

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.feature_extraction,
    pytest.mark.timeout(10)
]

class TestObservabilityDebug:
    """Debug test for observability validator"""

    async def test_observability_setup(self):
        """Test observability validator setup"""
        print("Creating observability validator...")
        observability = ObservabilityValidator()
        
        print("Starting observability capture...")
        observability.start_observability_capture()
        print("Observability capture started")
        
        print("Stopping observability capture...")
        observability.stop_observability_capture()
        print("Observability capture stopped")
        
        print("Clearing captures...")
        observability.clear_all_captures()
        print("Captures cleared")
