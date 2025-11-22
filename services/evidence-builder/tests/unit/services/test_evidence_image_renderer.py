"""Unit tests for EvidenceImageRenderer."""

import pytest
import numpy as np
import cv2
from unittest.mock import patch, MagicMock

from evidence_image_renderer import EvidenceImageRenderer


@pytest.fixture
def renderer():
    """Create EvidenceImageRenderer instance."""
    return EvidenceImageRenderer()


@pytest.fixture
def sample_image():
    """Create a sample image for testing."""
    return np.ones((100, 100, 3), dtype=np.uint8) * 128


def test_resize_image(renderer, sample_image):
    """Test image resizing."""
    target_height = 200
    
    resized = renderer._resize_image(sample_image, target_height)
    
    assert resized.shape[0] == target_height
    assert resized.shape[1] == 200  # Same aspect ratio


def test_resize_image_maintains_aspect_ratio(renderer):
    """Test that resize maintains aspect ratio."""
    img = np.ones((100, 200, 3), dtype=np.uint8)
    target_height = 400
    
    resized = renderer._resize_image(img, target_height)
    
    assert resized.shape[0] == 400
    assert resized.shape[1] == 800  # 2:1 aspect ratio maintained


def test_setup_canvas_and_place_images(renderer, sample_image):
    """Test canvas setup and image placement."""
    product_img = np.ones((400, 300, 3), dtype=np.uint8) * 100
    frame_img = np.ones((400, 350, 3), dtype=np.uint8) * 150
    
    combined = renderer._setup_canvas_and_place_images(product_img, frame_img)
    
    # Check canvas dimensions
    assert combined.shape[0] == 400 + 80 + 60  # height + header + footer
    assert combined.shape[1] == 300 + 350 + 60  # widths + padding
    assert combined.shape[2] == 3  # RGB


def test_add_text_and_borders(renderer):
    """Test adding text and borders to canvas."""
    canvas = np.ones((540, 710, 3), dtype=np.uint8) * 255
    
    result = renderer._add_text_and_borders(
        canvas,
        product_width=300,
        frame_width=350,
        score=0.95,
        timestamp=12.5,
        img_id="img_123",
        frame_id="frame_456",
        job_id="job_789"
    )
    
    assert result.shape == canvas.shape
    # Canvas should have been modified (not all white anymore)
    assert not np.all(result == 255)


def test_create_side_by_side_comparison_success(renderer, sample_image):
    """Test creating side-by-side comparison successfully."""
    product_img = np.ones((200, 150, 3), dtype=np.uint8) * 100
    frame_img = np.ones((200, 180, 3), dtype=np.uint8) * 150
    
    result = renderer.create_side_by_side_comparison(
        product_img,
        frame_img,
        score=0.92,
        timestamp=15.3,
        img_id="img_123",
        frame_id="frame_456",
        job_id="job_789"
    )
    
    assert result is not None
    assert len(result.shape) == 3
    assert result.shape[2] == 3  # RGB
    # Should be larger than original images due to padding and text
    assert result.shape[0] > 200
    assert result.shape[1] > 150 + 180


def test_create_side_by_side_comparison_handles_cv2_error(renderer, sample_image):
    """Test handling cv2 errors gracefully."""
    product_img = np.ones((200, 150, 3), dtype=np.uint8) * 100
    frame_img = np.ones((200, 180, 3), dtype=np.uint8) * 150
    
    with patch('cv2.resize', side_effect=cv2.error("Mock error")):
        result = renderer.create_side_by_side_comparison(
            product_img,
            frame_img,
            score=0.92,
            timestamp=15.3,
            img_id="img_123",
            frame_id="frame_456",
            job_id="job_789"
        )
        
        # Should return simple hstack as fallback
        assert result is not None
        assert result.shape[1] == product_img.shape[1] + frame_img.shape[1]


def test_create_side_by_side_comparison_handles_value_error(renderer):
    """Test handling ValueError gracefully."""
    product_img = np.ones((200, 150, 3), dtype=np.uint8) * 100
    frame_img = np.ones((200, 180, 3), dtype=np.uint8) * 150
    
    with patch.object(renderer, '_resize_image', side_effect=ValueError("Invalid dimensions")):
        result = renderer.create_side_by_side_comparison(
            product_img,
            frame_img,
            score=0.92,
            timestamp=15.3,
            img_id="img_123",
            frame_id="frame_456",
            job_id="job_789"
        )
        
        # Should return simple hstack as fallback
        assert result is not None


def test_create_side_by_side_comparison_with_different_sizes(renderer):
    """Test creating comparison with different sized images."""
    product_img = np.ones((300, 200, 3), dtype=np.uint8) * 100
    frame_img = np.ones((150, 400, 3), dtype=np.uint8) * 150
    
    result = renderer.create_side_by_side_comparison(
        product_img,
        frame_img,
        score=0.88,
        timestamp=5.0,
        img_id="img_abc",
        frame_id="frame_xyz",
        job_id="job_test"
    )
    
    assert result is not None
    assert len(result.shape) == 3


def test_create_side_by_side_comparison_with_extreme_scores(renderer, sample_image):
    """Test creating comparison with extreme score values."""
    product_img = np.ones((200, 150, 3), dtype=np.uint8) * 100
    frame_img = np.ones((200, 180, 3), dtype=np.uint8) * 150
    
    # Test with very low score
    result_low = renderer.create_side_by_side_comparison(
        product_img, frame_img, 0.001, 1.0, "img1", "frame1", "job1"
    )
    assert result_low is not None
    
    # Test with perfect score
    result_high = renderer.create_side_by_side_comparison(
        product_img, frame_img, 1.0, 1.0, "img2", "frame2", "job2"
    )
    assert result_high is not None


def test_create_side_by_side_comparison_with_long_ids(renderer, sample_image):
    """Test creating comparison with long ID strings."""
    product_img = np.ones((200, 150, 3), dtype=np.uint8) * 100
    frame_img = np.ones((200, 180, 3), dtype=np.uint8) * 150
    
    result = renderer.create_side_by_side_comparison(
        product_img,
        frame_img,
        score=0.85,
        timestamp=30.5,
        img_id="img_" + "x" * 50,
        frame_id="frame_" + "y" * 50,
        job_id="job_" + "z" * 50
    )
    
    assert result is not None


def test_resize_image_with_small_image(renderer):
    """Test resizing very small images."""
    small_img = np.ones((10, 10, 3), dtype=np.uint8)
    
    resized = renderer._resize_image(small_img, 400)
    
    assert resized.shape[0] == 400
    assert resized.shape[1] == 400


def test_resize_image_with_large_image(renderer):
    """Test resizing very large images."""
    large_img = np.ones((2000, 3000, 3), dtype=np.uint8)
    
    resized = renderer._resize_image(large_img, 400)
    
    assert resized.shape[0] == 400
    assert resized.shape[1] == 600  # Maintains 3:2 aspect ratio
