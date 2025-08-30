"""
Unit tests for KeyframeExtractor class
"""
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
import cv2
import numpy as np

from fetcher.keyframe_extractor import KeyframeExtractor, KeyframeConfig, VideoProperties


class TestKeyframeExtractor:
    """Test class for KeyframeExtractor"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def test_config(self):
        """Create test configuration"""
        config = KeyframeConfig()
        config.FRAME_QUALITY = 90
        config.MIN_BLUR_THRESHOLD = 50.0
        return config
    
    @pytest.fixture
    def extractor(self, temp_dir, test_config):
        """Create a KeyframeExtractor instance with temporary directory"""
        with patch('config_loader.config.KEYFRAME_DIR', temp_dir):
            return KeyframeExtractor(config_override=test_config)
    
    @pytest.fixture
    def sample_video(self, temp_dir):
        """Create a sample video file for testing"""
        video_path = Path(temp_dir) / "test_video.mp4"
        
        # Create a simple test video using OpenCV
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = 30
        frame_size = (640, 480)
        
        out = cv2.VideoWriter(str(video_path), fourcc, fps, frame_size)
        
        # Create 150 frames (5 seconds at 30fps)
        for i in range(150):
            # Create a frame with changing colors
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            # Change color over time
            frame[:, :] = (i % 255, (i * 2) % 255, (i * 3) % 255)
            # Add frame number text
            cv2.putText(frame, f"Frame {i}", (50, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            out.write(frame)
        
        out.release()
        return str(video_path)
    
    @pytest.mark.asyncio
    async def test_extract_keyframes_without_video_file(self, extractor):
        """Test keyframe extraction when no video file is provided"""
        video_id = "test_video_123"
        video_url = "https://example.com/video.mp4"
        
        # Extract keyframes without providing local_path
        keyframes = await extractor.extract_keyframes(video_url, video_id)
        
        # Should return empty list when no video file is available
        assert len(keyframes) == 0
    
    @pytest.mark.asyncio
    async def test_extract_keyframes_with_real_video(self, extractor, sample_video):
        """Test keyframe extraction from a real video file"""
        video_id = "test_video_456"
        video_url = "https://example.com/video.mp4"
        
        # Extract keyframes from the sample video
        keyframes = await extractor.extract_keyframes(video_url, video_id, sample_video)
        
        # Should extract frames from the video
        assert len(keyframes) > 0
        assert len(keyframes) <= 5  # Should not exceed max timestamps
        
        # Check that all keyframes have timestamp and path
        for timestamp, frame_path in keyframes:
            assert isinstance(timestamp, float)
            assert isinstance(frame_path, str)
            assert Path(frame_path).exists()
            assert Path(frame_path).suffix == ".jpg"
            assert timestamp >= 0.0  # Timestamps should be positive
    
    @pytest.mark.asyncio
    async def test_extract_keyframes_with_nonexistent_video(self, extractor):
        """Test keyframe extraction when video file doesn't exist"""
        video_id = "test_video_789"
        video_url = "https://example.com/video.mp4"
        nonexistent_path = "/path/that/does/not/exist.mp4"
        
        # Should return empty list when file doesn't exist
        keyframes = await extractor.extract_keyframes(video_url, video_id, nonexistent_path)
        
        # Should return empty list
        assert len(keyframes) == 0
    
    @pytest.mark.asyncio
    async def test_extract_keyframes_short_video(self, extractor, temp_dir):
        """Test keyframe extraction from a short video"""
        video_path = Path(temp_dir) / "short_video.mp4"
        
        # Create a short video (1 second, 30 frames)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = 30
        frame_size = (640, 480)
        
        out = cv2.VideoWriter(str(video_path), fourcc, fps, frame_size)
        
        for i in range(30):  # 1 second video
            frame = np.full((480, 640, 3), (100, 150, 200), dtype=np.uint8)
            cv2.putText(frame, f"Frame {i}", (50, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            out.write(frame)
        
        out.release()
        
        video_id = "short_video_test"
        
        # Extract keyframes
        keyframes = await extractor.extract_keyframes("test_url", video_id, str(video_path))
        
        # Should extract frames proportional to video length
        assert len(keyframes) > 0
        assert len(keyframes) <= 3  # Short video should have fewer keyframes
        
        # All timestamps should be within video duration
        for timestamp, _ in keyframes:
            assert 0 <= timestamp <= 1.0  # Video is 1 second long
    
    def test_calculate_blur_score_from_array(self, extractor):
        """Test blur score calculation from image array"""
        # Create a sharp image (high contrast edges)
        sharp_image = np.zeros((100, 100), dtype=np.uint8)
        sharp_image[40:60, 40:60] = 255  # White square on black background
        
        # Create a blurry image
        blurry_image = cv2.GaussianBlur(sharp_image, (15, 15), 5)
        
        sharp_score = extractor._calculate_blur_score(sharp_image)
        blurry_score = extractor._calculate_blur_score(blurry_image)
        
        # Sharp image should have higher blur score (more variance in Laplacian)
        assert sharp_score > blurry_score
        assert sharp_score > 0
        assert blurry_score >= 0
    
    def test_calculate_blur_score_from_file(self, extractor, temp_dir):
        """Test blur score calculation from image file"""
        # Create a test image file
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        image[40:60, 40:60] = (255, 255, 255)  # White square
        
        image_path = Path(temp_dir) / "test_image.jpg"
        cv2.imwrite(str(image_path), image)
        
        # Calculate blur score
        score = extractor.calculate_blur_score_from_file(str(image_path))
        assert score > 0
    
    def test_validate_inputs(self, extractor, sample_video):
        """Test input validation"""
        # Valid inputs
        assert extractor._validate_inputs("valid_id", sample_video) is True
        
        # Invalid video_id
        assert extractor._validate_inputs("", sample_video) is False
        assert extractor._validate_inputs("   ", sample_video) is False
        
        # Invalid local_path
        assert extractor._validate_inputs("valid_id", None) is False
        assert extractor._validate_inputs("valid_id", "/nonexistent/path.mp4") is False
    
    def test_create_keyframe_directory(self, extractor):
        """Test keyframe directory creation"""
        video_id = "test_directory_creation"
        
        # Should create directory successfully
        keyframe_dir = extractor._create_keyframe_directory(video_id)
        assert keyframe_dir is not None
        assert keyframe_dir.exists()
        assert keyframe_dir.is_dir()
    
    def test_calculate_extraction_timestamps(self, extractor):
        """Test timestamp calculation for different video durations"""
        # Short video (20 seconds)
        short_props = VideoProperties(fps=30, total_frames=600, duration=20.0, width=640, height=480)
        short_timestamps = extractor._calculate_extraction_timestamps(short_props)
        assert len(short_timestamps) == 3
        assert all(0 <= ts < 20.0 for ts in short_timestamps)
        
        # Medium video (45 seconds) - 50s timestamp should be filtered out
        medium_props = VideoProperties(fps=30, total_frames=1350, duration=45.0, width=640, height=480)
        medium_timestamps = extractor._calculate_extraction_timestamps(medium_props)
        assert len(medium_timestamps) == 2  # Only 10.0 and 30.0 should remain (50.0 filtered out)
        assert 10.0 in medium_timestamps
        assert 30.0 in medium_timestamps
        assert 50.0 not in medium_timestamps
        
        # Long video (180 seconds)
        long_props = VideoProperties(fps=30, total_frames=5400, duration=180.0, width=640, height=480)
        long_timestamps = extractor._calculate_extraction_timestamps(long_props)
        assert len(long_timestamps) == 5
        assert 10.0 in long_timestamps
        assert 120.0 in long_timestamps
        
        # Very short video (1 second)
        very_short_props = VideoProperties(fps=30, total_frames=30, duration=1.0, width=640, height=480)
        very_short_timestamps = extractor._calculate_extraction_timestamps(very_short_props)
        assert len(very_short_timestamps) == 1  # Should have middle timestamp
        assert very_short_timestamps[0] == 0.5
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_video(self, extractor, temp_dir):
        """Test error handling with invalid video file"""
        # Create a non-video file
        fake_video = Path(temp_dir) / "fake_video.mp4"
        fake_video.write_text("This is not a video file")
        
        video_id = "error_test_video"
        
        # Should handle error gracefully and return empty list
        keyframes = await extractor.extract_keyframes("test_url", video_id, str(fake_video))
        assert len(keyframes) == 0
    
    def test_video_properties_dataclass(self):
        """Test VideoProperties dataclass"""
        props = VideoProperties(fps=30.0, total_frames=900, duration=30.0, width=1920, height=1080)
        
        assert props.fps == 30.0
        assert props.total_frames == 900
        assert props.duration == 30.0
        assert props.width == 1920
        assert props.height == 1080
    
    def test_keyframe_config_dataclass(self):
        """Test KeyframeConfig dataclass"""
        config = KeyframeConfig()
        
        assert len(config.SHORT_VIDEO_RATIO) == 3
        assert len(config.MEDIUM_VIDEO_TIMESTAMPS) == 3
        assert len(config.LONG_VIDEO_TIMESTAMPS) == 4
        assert len(config.VERY_LONG_VIDEO_TIMESTAMPS) == 5
        assert config.MIN_BLUR_THRESHOLD == 100.0
        assert config.FRAME_BUFFER_SECONDS == 1.0
        assert config.FRAME_QUALITY == 95
        assert config.FRAME_FORMAT == "jpg"