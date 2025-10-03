import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import numpy as np
from PIL import Image

# Ensure unit tests can be selected via `-m unit`
pytestmark = pytest.mark.unit

# Import the service and models
from services.matcher_service import MatcherService
from services.data_models import Product, VideoFrame, MatchResult

# Mock data for testing
MOCK_PRODUCT = Product(
    product_id="P123",
    image_url="http://example.com/product.jpg",
    metadata={}
)
MOCK_FRAME = VideoFrame(
    frame_id="F456",
    video_id="V789",
    timestamp=10.5,
    image_url="http://example.com/frame.jpg"
)
MOCK_MATCH_RESULT = MatchResult(
    product_id="P123",
    frame_id="F456",
    match_score=0.8,
    bounding_box=[10, 20, 100, 200],
    confidence_level=0.9
)

@pytest.fixture
def matcher_service_mocked():
    """Fixture for MatcherService with mocked dependencies."""
    # We need to mock the __init__ to prevent loading heavy models
    with patch('services.matcher_service.CLIPModel'), \
         patch('services.matcher_service.CLIPProcessor'), \
         patch('services.matcher_service.cv2.AKAZE_create'), \
         patch('services.matcher_service.cv2.BFMatcher'):
        service = MatcherService()
        # Mock the internal methods
        service._load_image_from_url = AsyncMock(return_value=Image.new('RGB', (100, 100)))
        
        # Mock the CLIP embedding to return a simple vector for similarity calculation
        # The actual similarity calculation is done inside the match method
        def mock_clip_embedding(image):
            # Simple mock: return a vector based on the image object's hash for distinctness
            # In a real test, we'd return pre-calculated vectors
            if 'product' in service._load_image_from_url.call_args_list[0][0][0]:
                return np.array([1.0, 0.0]) # Mock product vector
            return np.array([0.9, 0.1]) # Mock frame vector (high similarity by default)

        service._get_clip_embedding = MagicMock(side_effect=mock_clip_embedding)
        service._perform_cv_match = MagicMock(return_value=MOCK_MATCH_RESULT)
        return service

@pytest.mark.asyncio
async def test_match_success_flow(matcher_service_mocked):
    """Tests the end-to-end successful matching flow."""
    # Set up mocks for high similarity
    matcher_service_mocked._get_clip_embedding.side_effect = [
        np.array([1.0, 0.0]), # Product embedding
        np.array([0.9, 0.1])  # Frame embedding (high similarity)
    ]
    
    results = await matcher_service_mocked.match(MOCK_PRODUCT, MOCK_FRAME)

    assert len(results) == 1
    assert results[0].product_id == MOCK_PRODUCT.product_id
    assert results[0].frame_id == MOCK_FRAME.frame_id
    # Check that the final score is a combination of CV score (0.8) and CLIP similarity (~0.9)
    # Cosine similarity of [1,0] and [0.9, 0.1] is approx 0.994.
    # Final score: 0.8 * 0.7 + 0.994 * 0.3 = 0.56 + 0.2982 = 0.8582
    assert results[0].match_score == pytest.approx(0.8582, abs=1e-4)

@pytest.mark.asyncio
async def test_match_clip_filter_fail(matcher_service_mocked):
    """Tests that the match fails if CLIP similarity is too low."""
    # Set up mocks for low similarity (e.g., 0.1)
    matcher_service_mocked._get_clip_embedding.side_effect = [
        np.array([1.0, 0.0]), # Product embedding
        np.array([0.0, 1.0])  # Frame embedding (zero similarity)
    ]
    
    results = await matcher_service_mocked.match(MOCK_PRODUCT, MOCK_FRAME)

    assert len(results) == 0
    # Ensure CV match was not called
    matcher_service_mocked._perform_cv_match.assert_not_called()

@pytest.mark.asyncio
async def test_match_cv_filter_fail(matcher_service_mocked):
    """Tests that the match fails if CV match is not robust."""
    # Set up mocks for high similarity
    matcher_service_mocked._get_clip_embedding.side_effect = [
        np.array([1.0, 0.0]), # Product embedding
        np.array([0.9, 0.1])  # Frame embedding (high similarity)
    ]
    
    # Mock CV match to return None
    matcher_service_mocked._perform_cv_match.return_value = None
    
    results = await matcher_service_mocked.match(MOCK_PRODUCT, MOCK_FRAME)
    assert len(results) == 0
    # Ensure CV match was called
    matcher_service_mocked._perform_cv_match.assert_called_once()

@pytest.mark.asyncio
async def test_match_image_load_fail(matcher_service_mocked):
    """Tests that the match fails if image loading fails."""
    # Mock image loading to return None
    matcher_service_mocked._load_image_from_url.return_value = None
    
    results = await matcher_service_mocked.match(MOCK_PRODUCT, MOCK_FRAME)

    assert len(results) == 0
    # Ensure no further processing was attempted
    matcher_service_mocked._get_clip_embedding.assert_not_called()
    matcher_service_mocked._perform_cv_match.assert_not_called()
