import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import numpy as np
import pytest

from keypoint import KeypointExtractor


class TestKeypointExtractor:
    """Unit tests for KeypointExtractor class"""

    def setup_method(self):
        """Setup for each test"""
        self.test_dir = tempfile.mkdtemp()
        self.extractor = KeypointExtractor(self.test_dir)

    @pytest.mark.unit
    def test_init_creates_keypoint_directory(self):
        """Test that initialization creates the keypoint directory"""
        assert self.extractor.kp_dir.exists()
        assert self.extractor.kp_dir.is_dir()

    @pytest.mark.unit
    @patch('keypoint.cv2.imread')
    @patch('keypoint.cv2.resize')
    @patch('keypoint.np.savez_compressed')
    @patch('keypoint.np.random.randint')
    @patch('keypoint.np.random.uniform')
    @patch('pathlib.Path.mkdir')
    async def test_extract_keypoints_success_with_akaze(self, mock_mkdir, mock_uniform, mock_randint,
                                                        mock_savez, mock_resize, mock_imread):
        """Test successful keypoint extraction with AKAZE"""
        # Setup mocks
        mock_imread.return_value = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
        mock_resize.return_value = np.random.randint(0, 255, (64, 64), dtype=np.uint8)

        # Mock keypoints and descriptors
        mock_keypoint = Mock()
        mock_keypoint.pt = (10, 20)
        mock_keypoint.angle = 45.0
        mock_keypoint.response = 0.8
        mock_keypoint.octave = 1
        mock_keypoint.size = 5.0

        mock_akaze_instance = Mock()
        mock_akaze_instance.detectAndCompute.return_value = ([mock_keypoint],
                                                             np.random.randint(0, 255, (1, 64), dtype=np.uint8))

        self.extractor.akaze = mock_akaze_instance

        # Test the method
        result = await self.extractor.extract_keypoints("fake_image_path.jpg", "test_entity_123")

        # Assertions
        assert result is not None
        mock_imread.assert_called_once_with("fake_image_path.jpg", 0)  # cv2.IMREAD_GRAYSCALE is 0
        mock_akaze_instance.detectAndCompute.assert_called_once()

    @pytest.mark.unit
    @patch('keypoint.cv2.imread')
    @patch('keypoint.cv2.resize')
    @patch('keypoint.np.savez_compressed')
    @patch('keypoint.np.random.randint')
    @patch('keypoint.np.random.uniform')
    async def test_extract_keypoints_fallback_to_sift(self, mock_uniform, mock_randint,
                                                      mock_savez, mock_resize, mock_imread):
        """Test fallback to SIFT when AKAZE finds insufficient keypoints"""
        # Setup mocks
        mock_imread.return_value = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
        mock_resize.return_value = np.random.randint(0, 255, (64, 64), dtype=np.uint8)

        # Mock AKAZE to return few keypoints
        mock_akaze_instance = Mock()
        mock_akaze_instance.detectAndCompute.return_value = ([Mock() for _ in range(5)],
                                                             np.random.randint(0, 255, (5, 64), dtype=np.uint8))

        # Mock SIFT to return sufficient keypoints
        mock_keypoint = Mock()
        mock_keypoint.pt = (15, 25)
        mock_keypoint.angle = 60.0
        mock_keypoint.response = 0.9
        mock_keypoint.octave = 2
        mock_keypoint.size = 6.0

        mock_sift_instance = Mock()
        mock_sift_instance.detectAndCompute.return_value = ([mock_keypoint],
                                                            np.random.randint(0, 255, (1, 128), dtype=np.uint8))

        self.extractor.akaze = mock_akaze_instance
        self.extractor.sift = mock_sift_instance

        # Test the method
        result = await self.extractor.extract_keypoints("fake_image_path.jpg", "test_entity_123")

        # Assertions
        assert result is not None
        mock_akaze_instance.detectAndCompute.assert_called_once()
        mock_sift_instance.detectAndCompute.assert_called_once()

    @pytest.mark.unit
    @patch('keypoint.cv2.imread')
    @patch('keypoint.cv2.resize')
    @patch('keypoint.np.savez_compressed')
    @patch('keypoint.np.random.randint')
    @patch('keypoint.np.random.uniform')
    def test_load_keypoints_success(self, mock_uniform, mock_randint,
                                    mock_savez, mock_resize, mock_imread):
        """Test successful loading of keypoints from file"""
        import numpy as np

        # Create a realistic mock for np.load result that has the expected structure
        mock_loaded_data = MagicMock()

        # Mock the keypoints data
        mock_keypoints_data = np.array([{
            "pt": (10, 20),
            "angle": 45.0,
            "response": 0.8,
            "octave": 1,
            "size": 5.0,
        }])

        # Mock the descriptors with the correct shape
        mock_descriptors = MagicMock()
        mock_descriptors.shape = (1, 64)
        mock_descriptors.__len__ = lambda: 1

        # Configure the mock to return the expected values when indexed
        mock_loaded_data.__getitem__.side_effect = lambda key: {
            "keypoints": mock_keypoints_data,
            "descriptors": mock_descriptors
        }[key]

        with patch('keypoint.np.load', return_value=mock_loaded_data):
            # Create a temporary file path
            fake_path = str(Path(self.test_dir) / "fake_keypoints.npz")

            # Test the method
            keypoints, descriptors = self.extractor.load_keypoints(fake_path)

            # Assertions
            assert len(keypoints) == 1
            assert descriptors.shape == (1, 64)

    @pytest.mark.unit
    @patch('keypoint.cv2.imread')
    @patch('keypoint.cv2.resize')
    @patch('keypoint.cv2.bitwise_and')
    @patch('keypoint.np.savez_compressed')
    @patch('keypoint.cv2.KeyPoint')
    @patch('keypoint.np.random.randint')
    @patch('keypoint.np.random.uniform')
    async def test_extract_keypoints_with_mask_success(self, mock_uniform, mock_randint,
                                                       mock_keypoint_cls, mock_savez, mock_bitwise_and,
                                                       mock_resize, mock_imread):
        """Test successful keypoint extraction with mask"""
        # Setup mocks
        mock_imread.side_effect = [
            np.random.randint(0, 255, (100, 100), dtype=np.uint8),  # image
            np.random.randint(0, 255, (100, 100), dtype=np.uint8)   # mask
        ]
        mock_resize.side_effect = [
            np.random.randint(0, 255, (64, 64), dtype=np.uint8),  # resized image
            np.random.randint(0, 255, (64, 64), dtype=np.uint8)   # resized mask
        ]

        # Mock the bitwise_and to return the masked image
        mock_bitwise_and.return_value = np.random.randint(0, 255, (64, 64), dtype=np.uint8)

        # Mock keypoints and descriptors
        mock_keypoint = Mock()
        mock_keypoint.pt = (10, 20)
        mock_keypoint.angle = 45.0
        mock_keypoint.response = 0.8
        mock_keypoint.octave = 1
        mock_keypoint.size = 5.0

        mock_akaze_instance = Mock()
        mock_akaze_instance.detectAndCompute.return_value = ([mock_keypoint],
                                                             np.random.randint(0, 255, (1, 64), dtype=np.uint8))

        self.extractor.akaze = mock_akaze_instance

        # Test the method
        result = await self.extractor.extract_keypoints_with_mask("fake_image_path.jpg",
                                                                  "fake_mask_path.jpg",
                                                                  "test_entity_123")

        # Assertions
        assert result is not None
        assert mock_imread.call_count == 2  # Once for image, once for mask
        mock_akaze_instance.detectAndCompute.assert_called_once()

    @pytest.mark.unit
    @patch('keypoint.cv2.imread')
    async def test_extract_keypoints_fails_to_load_image(self, mock_imread):
        """Test that extracting keypoints fails when image can't be loaded"""
        # Setup mock
        mock_imread.return_value = None  # Simulate failure to load

        # Test the method
        result = await self.extractor.extract_keypoints("fake_image_path.jpg", "test_entity_123")

        # Assertions
        assert result is None
        mock_imread.assert_called_once_with("fake_image_path.jpg", 0)  # cv2.IMREAD_GRAYSCALE is 0
