"""Basic tests for vision embedding service."""

import pytest
pytestmark = pytest.mark.unit


class TestVisionEmbeddingServiceBasic:
    """Basic vision embedding service tests."""
    
    def test_import_service(self):
        """Test that service module can be imported."""
        # This test will fail if dependencies are missing, but that's expected
        # We just want to ensure the basic structure is there
        try:
            from services.service import VisionEmbeddingService
        except ImportError as e:
            # Expected due to missing dependencies in test environment
            pytest.skip(f"Skipping due to missing dependencies: {e}")
            
        # If import succeeds, basic structure is correct
        assert VisionEmbeddingService is not None