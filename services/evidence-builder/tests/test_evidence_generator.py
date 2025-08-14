import pytest
import numpy as np
import cv2
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import shutil

from evidence import EvidenceGenerator


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def evidence_generator(temp_dir):
    """Create an EvidenceGenerator instance with a temporary directory"""
    return EvidenceGenerator(temp_dir)


@pytest.fixture
def sample_images():
    """Create sample images for testing"""
    # Create sample product image (red square)
    product_img = np.zeros((200, 200, 3), dtype=np.uint8)
    product_img[:, :] = [0, 0, 255]  # Red
    
    # Create sample frame image (blue square)
    frame_img = np.zeros((200, 200, 3), dtype=np.uint8)
    frame_img[:, :] = [255, 0, 0]  # Blue
    
    return product_img, frame_img


def test_evidence_generator_initialization(temp_dir):
    """Test that EvidenceGenerator initializes correctly"""
    generator = EvidenceGenerator(temp_dir)
    assert generator.data_root == Path(temp_dir)
    assert generator.evidence_dir == Path(temp_dir) / "evidence"
    assert generator.evidence_dir.exists()


def test_create_side_by_side_comparison(evidence_generator, sample_images):
    """Test creating side-by-side comparison image"""
    product_img, frame_img = sample_images
    
    result = evidence_generator.create_side_by_side_comparison(
        product_img, frame_img, 0.95, 10.5, "img123", "frame456"
    )
    
    # Check that result is a valid image
    assert result is not None
    assert isinstance(result, np.ndarray)
    assert len(result.shape) == 3  # Should be a 3-channel image


def test_create_evidence(evidence_generator, sample_images, temp_dir):
    """Test creating evidence image"""
    product_img, frame_img = sample_images
    
    # Save sample images to temporary files
    product_path = Path(temp_dir) / "product.jpg"
    frame_path = Path(temp_dir) / "frame.jpg"
    
    cv2.imwrite(str(product_path), product_img)
    cv2.imwrite(str(frame_path), frame_img)
    
    # Create evidence
    evidence_path = evidence_generator.create_evidence(
        str(product_path),
        str(frame_path),
        "img123",
        "frame456",
        0.95,
        10.5
    )
    
    # Check that evidence was created
    assert evidence_path is not None
    assert Path(evidence_path).exists()
    assert "img123_frame456_evidence.jpg" in evidence_path


def test_create_evidence_with_keypoints(evidence_generator, sample_images, temp_dir):
    """Test creating evidence image with keypoint overlays"""
    product_img, frame_img = sample_images
    
    # Save sample images to temporary files
    product_path = Path(temp_dir) / "product.jpg"
    frame_path = Path(temp_dir) / "frame.jpg"
    
    cv2.imwrite(str(product_path), product_img)
    cv2.imwrite(str(frame_path), frame_img)
    
    # Create evidence with mock keypoint paths
    evidence_path = evidence_generator.create_evidence(
        str(product_path),
        str(frame_path),
        "img123",
        "frame456",
        0.95,
        10.5,
        "mock_kp_img_path",
        "mock_kp_frame_path"
    )
    
    # Check that evidence was created
    assert evidence_path is not None
    assert Path(evidence_path).exists()


def test_create_evidence_missing_images(evidence_generator):
    """Test creating evidence with missing images"""
    evidence_path = evidence_generator.create_evidence(
        "/nonexistent/product.jpg",
        "/nonexistent/frame.jpg",
        "img123",
        "frame456",
        0.95,
        10.5
    )
    
    # Should return None for missing images
    assert evidence_path is None