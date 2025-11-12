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

    @pytest.mark.unit
    @patch('keypoint.cv2.imread')
    async def test_extract_keypoints_too_few_keypoints_triggers_sift_fallback(self, mock_imread):
        """Test that AKAZE with too few keypoints triggers SIFT fallback"""
        # Setup mocks
        mock_imread.return_value = np.random.randint(0, 255, (100, 100), dtype=np.uint8)

        # Mock AKAZE to return insufficient keypoints (< 10)
        mock_akaze_instance = Mock()
        mock_akaze_instance.detectAndCompute.return_value = ([Mock() for _ in range(5)],
                                                             np.random.randint(0, 255, (5, 64), dtype=np.uint8))

        # Mock SIFT to also return insufficient keypoints (< 5)
        mock_sift_instance = Mock()
        mock_sift_instance.detectAndCompute.return_value = ([Mock() for _ in range(3)],
                                                            np.random.randint(0, 255, (3, 128), dtype=np.uint8))

        self.extractor.akaze = mock_akaze_instance
        self.extractor.sift = mock_sift_instance

        # Mock _create_mock_keypoints to return a path
        with patch.object(self.extractor, '_create_mock_keypoints', return_value="mock_path.npz"):
            result = await self.extractor.extract_keypoints("fake_image_path.jpg", "test_entity_123")

        # Assertions
        assert result == "mock_path.npz"
        mock_akaze_instance.detectAndCompute.assert_called_once()
        mock_sift_instance.detectAndCompute.assert_called_once()

    @pytest.mark.unit
    @patch('keypoint.cv2.imread')
    async def test_extract_keypoints_both_detectors_fail(self, mock_imread):
        """Test mock keypoint creation when both detectors fail"""
        # Setup mocks
        mock_imread.return_value = np.random.randint(0, 255, (100, 100), dtype=np.uint8)

        # Mock both AKAZE and SIFT to fail
        mock_akaze_instance = Mock()
        mock_akaze_instance.detectAndCompute.return_value = ([], None)

        mock_sift_instance = Mock()
        mock_sift_instance.detectAndCompute.return_value = ([], None)

        self.extractor.akaze = mock_akaze_instance
        self.extractor.sift = mock_sift_instance

        # Mock _create_mock_keypoints to return a path
        with patch.object(self.extractor, '_create_mock_keypoints', return_value="mock_path.npz"):
            result = await self.extractor.extract_keypoints("fake_image_path.jpg", "test_entity_123")

        # Assertions
        assert result == "mock_path.npz"
        mock_akaze_instance.detectAndCompute.assert_called_once()
        mock_sift_instance.detectAndCompute.assert_called_once()

    @pytest.mark.unit
    @patch('keypoint.cv2.imread')
    @patch('keypoint.cv2.resize')
    async def test_extract_keypoints_save_keypoints_raises(self, mock_resize, mock_imread):
        """Test broad exception handler when _save_keypoints raises"""
        # Setup mocks
        mock_imread.return_value = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
        mock_resize.return_value = np.random.randint(0, 255, (64, 64), dtype=np.uint8)

        # Mock successful keypoint detection with enough keypoints
        mock_keypoints = []
        for i in range(15):  # More than 10 to avoid SIFT fallback
            mock_kp = Mock()
            mock_kp.pt = (10 + i, 20 + i)
            mock_kp.angle = 45.0
            mock_kp.response = 0.8
            mock_kp.octave = 1
            mock_kp.size = 5.0
            mock_keypoints.append(mock_kp)

        mock_akaze_instance = Mock()
        mock_akaze_instance.detectAndCompute.return_value = (mock_keypoints,
                                                             np.random.randint(0, 255, (15, 64), dtype=np.uint8))

        self.extractor.akaze = mock_akaze_instance

        # Mock _save_keypoints to raise an exception
        with patch.object(self.extractor, '_save_keypoints', side_effect=IOError("Disk full")):
            result = await self.extractor.extract_keypoints("fake_image_path.jpg", "test_entity_123")

        # Assertions - should return None due to broad exception handler
        assert result is None
        mock_akaze_instance.detectAndCompute.assert_called_once()

    @pytest.mark.unit
    @patch('keypoint.np.load')
    def test_load_keypoints_failure_handling(self, mock_np_load):
        """Test load_keypoints failure handling"""
        # Setup mock to raise an exception
        mock_np_load.side_effect = FileNotFoundError("File not found")

        # Test the method
        keypoints, descriptors = self.extractor.load_keypoints("nonexistent_path.npz")

        # Assertions - should return empty results due to exception handler
        assert keypoints == []
        assert descriptors.shape == (0,)  # Empty array
        assert np.array_equal(descriptors, np.array([]))

    @pytest.mark.unit
    @patch('keypoint.cv2.imread')
    @patch('keypoint.cv2.resize')
    @patch('keypoint.cv2.bitwise_and')
    async def test_extract_keypoints_with_mask_fails_to_load_image(self, mock_bitwise_and, mock_resize, mock_imread):
        """Test masked extraction fails when image can't be loaded"""
        # Setup mock to return None for image (failure)
        mock_imread.return_value = None

        # Test the method
        result = await self.extractor.extract_keypoints_with_mask("fake_image_path.jpg",
                                                                  "fake_mask_path.jpg",
                                                                  "test_entity_123")

        # Assertions
        assert result is None
        mock_imread.assert_called_once_with("fake_image_path.jpg", 0)  # cv2.IMREAD_GRAYSCALE is 0

    @pytest.mark.unit
    @patch('keypoint.cv2.imread')
    @patch('keypoint.cv2.resize')
    async def test_extract_keypoints_with_mask_fails_to_load_mask(self, mock_resize, mock_imread):
        """Test masked extraction fails when mask can't be loaded"""
        # Setup mocks
        mock_imread.side_effect = [
            np.random.randint(0, 255, (100, 100), dtype=np.uint8),  # image loads successfully
            None  # mask fails to load
        ]
        mock_resize.return_value = np.random.randint(0, 255, (64, 64), dtype=np.uint8)

        # Test the method
        result = await self.extractor.extract_keypoints_with_mask("fake_image_path.jpg",
                                                                  "fake_mask_path.jpg",
                                                                  "test_entity_123")

        # Assertions
        assert result is None
        assert mock_imread.call_count == 2

    @pytest.mark.unit
    @patch('keypoint.cv2.imread')
    @patch('keypoint.cv2.resize')
    @patch('keypoint.cv2.bitwise_and')
    async def test_extract_keypoints_with_mask_insufficient_keypoints(self, mock_bitwise_and, mock_resize, mock_imread):
        """Test masked extraction with insufficient keypoints triggers mock creation"""
        # Setup mocks
        mock_imread.side_effect = [
            np.random.randint(0, 255, (100, 100), dtype=np.uint8),  # image
            np.random.randint(0, 255, (100, 100), dtype=np.uint8)   # mask
        ]
        mock_resize.side_effect = [
            np.random.randint(0, 255, (64, 64), dtype=np.uint8),  # resized image
            np.random.randint(0, 255, (64, 64), dtype=np.uint8)   # resized mask
        ]
        mock_bitwise_and.return_value = np.random.randint(0, 255, (64, 64), dtype=np.uint8)

        # Mock both AKAZE and SIFT to return insufficient keypoints
        mock_akaze_instance = Mock()
        mock_akaze_instance.detectAndCompute.return_value = ([Mock() for _ in range(3)],
                                                             np.random.randint(0, 255, (3, 64), dtype=np.uint8))

        mock_sift_instance = Mock()
        mock_sift_instance.detectAndCompute.return_value = ([Mock() for _ in range(2)],
                                                            np.random.randint(0, 255, (2, 128), dtype=np.uint8))

        self.extractor.akaze = mock_akaze_instance
        self.extractor.sift = mock_sift_instance

        # Mock _create_mock_keypoints to return a path
        with patch.object(self.extractor, '_create_mock_keypoints', return_value="mock_path.npz"):
            result = await self.extractor.extract_keypoints_with_mask("fake_image_path.jpg",
                                                                      "fake_mask_path.jpg",
                                                                      "test_entity_123")

        # Assertions
        assert result == "mock_path.npz"
        mock_akaze_instance.detectAndCompute.assert_called_once()
        mock_sift_instance.detectAndCompute.assert_called_once()

    @pytest.mark.unit
    @patch('keypoint.np.random.randint')
    @patch('keypoint.np.random.uniform')
    @patch('keypoint.np.savez_compressed')
    async def test_create_mock_keypoints_failure(self, mock_savez, mock_uniform, mock_randint):
        """Test _create_mock_keypoints failure handling"""
        # Setup mocks to avoid recursion
        mock_randint.return_value = 50  # number of keypoints
        mock_uniform.return_value = 0.5  # Simple return value

        # Mock np.savez_compressed to raise an exception
        mock_savez.side_effect = IOError("Failed to save mock keypoints")

        # Test the method
        result = await self.extractor._create_mock_keypoints("test_entity_123")

        # Assertions - should return None due to exception handler
        assert result is None
        mock_savez.assert_called_once()

    @pytest.mark.unit
    @patch('keypoint.np.random.randint')
    @patch('keypoint.np.random.uniform')
    @patch('keypoint.np.savez_compressed')
    @patch('pathlib.Path.mkdir')
    async def test_extract_akaze_keypoints_with_mask(self, mock_mkdir, mock_savez, mock_uniform, mock_randint):
        """Test _extract_akaze_keypoints_with_mask method"""
        # Setup mocks
        mock_mkdir.return_value = None

        # Mock AKAZE instance
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

        # Create test image and mask
        image = np.random.randint(0, 255, (64, 64), dtype=np.uint8)
        mask = np.random.randint(0, 255, (64, 64), dtype=np.uint8)

        # Test the method
        keypoints, descriptors = await self.extractor._extract_akaze_keypoints_with_mask(image, mask)

        # Assertions
        assert len(keypoints) == 1
        assert descriptors is not None
        mock_akaze_instance.detectAndCompute.assert_called_once_with(image, mask)

    @pytest.mark.unit
    @patch('keypoint.np.random.randint')
    @patch('keypoint.np.random.uniform')
    @patch('keypoint.np.savez_compressed')
    @patch('pathlib.Path.mkdir')
    async def test_extract_sift_keypoints_with_mask(self, mock_mkdir, mock_savez, mock_uniform, mock_randint):
        """Test _extract_sift_keypoints_with_mask method"""
        # Setup mocks
        mock_mkdir.return_value = None

        # Mock SIFT instance
        mock_keypoint = Mock()
        mock_keypoint.pt = (10, 20)
        mock_keypoint.angle = 45.0
        mock_keypoint.response = 0.8
        mock_keypoint.octave = 1
        mock_keypoint.size = 5.0

        mock_sift_instance = Mock()
        mock_sift_instance.detectAndCompute.return_value = ([mock_keypoint],
                                                            np.random.randint(0, 255, (1, 128), dtype=np.uint8))

        self.extractor.sift = mock_sift_instance

        # Create test image and mask
        image = np.random.randint(0, 255, (64, 64), dtype=np.uint8)
        mask = np.random.randint(0, 255, (64, 64), dtype=np.uint8)

        # Test the method
        keypoints, descriptors = await self.extractor._extract_sift_keypoints_with_mask(image, mask)

        # Assertions
        assert len(keypoints) == 1
        assert descriptors is not None
        mock_sift_instance.detectAndCompute.assert_called_once_with(image, mask)

    @pytest.mark.unit
    async def test_extract_akaze_keypoints_failure(self):
        """Test _extract_akaze_keypoints exception handling"""
        # Mock AKAZE instance to raise an exception
        mock_akaze_instance = Mock()
        mock_akaze_instance.detectAndCompute.side_effect = RuntimeError("AKAZE failed")

        self.extractor.akaze = mock_akaze_instance

        # Create test image
        image = np.random.randint(0, 255, (64, 64), dtype=np.uint8)

        # Test the method
        keypoints, descriptors = await self.extractor._extract_akaze_keypoints(image)

        # Assertions - should return empty results due to exception handler
        assert keypoints == []
        assert descriptors is None

    @pytest.mark.unit
    async def test_extract_sift_keypoints_failure(self):
        """Test _extract_sift_keypoints exception handling"""
        # Mock SIFT instance to raise an exception
        mock_sift_instance = Mock()
        mock_sift_instance.detectAndCompute.side_effect = RuntimeError("SIFT failed")

        self.extractor.sift = mock_sift_instance

        # Create test image
        image = np.random.randint(0, 255, (64, 64), dtype=np.uint8)

        # Test the method
        keypoints, descriptors = await self.extractor._extract_sift_keypoints(image)

        # Assertions - should return empty results due to exception handler
        assert keypoints == []
        assert descriptors is None

    @pytest.mark.unit
    async def test_extract_akaze_keypoints_with_mask_failure(self):
        """Test _extract_akaze_keypoints_with_mask exception handling"""
        # Mock AKAZE instance to raise an exception
        mock_akaze_instance = Mock()
        mock_akaze_instance.detectAndCompute.side_effect = RuntimeError("AKAZE with mask failed")

        self.extractor.akaze = mock_akaze_instance

        # Create test image and mask
        image = np.random.randint(0, 255, (64, 64), dtype=np.uint8)
        mask = np.random.randint(0, 255, (64, 64), dtype=np.uint8)

        # Test the method
        keypoints, descriptors = await self.extractor._extract_akaze_keypoints_with_mask(image, mask)

        # Assertions - should return empty results due to exception handler
        assert keypoints == []
        assert descriptors is None

    @pytest.mark.unit
    async def test_extract_sift_keypoints_with_mask_failure(self):
        """Test _extract_sift_keypoints_with_mask exception handling"""
        # Mock SIFT instance to raise an exception
        mock_sift_instance = Mock()
        mock_sift_instance.detectAndCompute.side_effect = RuntimeError("SIFT with mask failed")

        self.extractor.sift = mock_sift_instance

        # Create test image and mask
        image = np.random.randint(0, 255, (64, 64), dtype=np.uint8)
        mask = np.random.randint(0, 255, (64, 64), dtype=np.uint8)

        # Test the method
        keypoints, descriptors = await self.extractor._extract_sift_keypoints_with_mask(image, mask)

        # Assertions - should return empty results due to exception handler
        assert keypoints == []
        assert descriptors is None
