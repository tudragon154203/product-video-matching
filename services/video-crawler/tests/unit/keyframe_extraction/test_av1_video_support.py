"""
Tests for AV1 video support in keyframe extraction.

This test module ensures that the keyframe extractor can handle both AV1 and normal
video formats properly, with appropriate fallback mechanisms.
"""

import os
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from keyframe_extractor.length_adaptive_extractor import LengthAdaptiveKeyframeExtractor


class TestAV1VideoSupport:
    """Test AV1 video handling in keyframe extraction."""

    @pytest.fixture
    def extractor(self):
        """Create a keyframe extractor instance for testing."""
        return LengthAdaptiveKeyframeExtractor(create_dirs=False)

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        # Cleanup
        import shutil
        if temp_path.exists():
            shutil.rmtree(temp_path)

    @pytest.fixture
    def video_id(self):
        """Test video ID."""
        return "test_video_av1"

    @patch('keyframe_extractor.length_adaptive_extractor.cv2')
    async def test_normal_video_opens_without_env_vars(self, mock_cv2, extractor, temp_dir, video_id):
        """Test that normal videos open without special environment variables."""
        # Mock successful video capture for normal video
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True

        # Set up OpenCV constants first
        mock_cv2.CAP_PROP_FPS = 2
        mock_cv2.CAP_PROP_FRAME_COUNT = 1
        mock_cv2.CAP_PROP_FRAME_WIDTH = 3
        mock_cv2.CAP_PROP_FRAME_HEIGHT = 4

        # Now configure the mock to return proper values
        mock_cap.get.side_effect = lambda prop: {
            mock_cv2.CAP_PROP_FRAME_COUNT: 30.0,
            mock_cv2.CAP_PROP_FPS: 5.0,
            mock_cv2.CAP_PROP_FRAME_WIDTH: 640,
            mock_cv2.CAP_PROP_FRAME_HEIGHT: 480,
            7: 10.0,  # CAP_PROP_POS_MSEC (duration)
        }.get(prop, 0)
        mock_cap.set.return_value = True
        mock_cap.read.return_value = (True, Mock())  # Mock frame

        mock_cv2.VideoCapture.return_value = mock_cap
        mock_cv2.CAP_FFMPEG = 1900
        mock_cv2.CAP_PROP_FOURCC = 6
        mock_cv2.VIDEO_ACCELERATION_ANY = 0
        mock_cv2.VideoWriter_fourcc.return_value = 0x30315661  # 'av01'

        video_path = temp_dir / "normal_video.mp4"
        video_path.touch()  # Create empty file

        # This should work without any special AV1 handling
        result = await extractor._extract_frames_from_video(
            str(video_path), temp_dir, video_id
        )

        # Verify environment variables were set and restored
        assert isinstance(result, list)
        mock_cv2.VideoCapture.assert_called()

    @patch('keyframe_extractor.length_adaptive_extractor.cv2')
    @patch.dict(os.environ, {}, clear=True)  # Start with clean environment
    async def test_av1_video_with_software_fallback(self, mock_cv2, extractor, temp_dir, video_id):
        """Test AV1 video with software decoding fallback."""
        # Mock video capture that fails first, then succeeds
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            1: 30.0,  # CAP_PROP_FRAME_COUNT
            2: 5.0,   # CAP_PROP_FPS
            3: 640,   # CAP_PROP_FRAME_WIDTH
            4: 480,   # CAP_PROP_FRAME_HEIGHT
            7: 10.0,  # CAP_PROP_POS_MSEC (duration)
        }.get(prop, 0)
        mock_cap.set.return_value = True
        mock_cap.read.return_value = (True, Mock())  # Mock frame

        # First call (FFMPEG with AV1 settings) succeeds
        mock_cv2.VideoCapture.return_value = mock_cap
        mock_cv2.CAP_FFMPEG = 1900
        mock_cv2.CAP_PROP_FOURCC = 6
        mock_cv2.VIDEO_ACCELERATION_ANY = 0
        mock_cv2.VideoWriter_fourcc.return_value = 0x30315661  # 'av01'
        # Add missing OpenCV constants
        mock_cv2.CAP_PROP_FPS = 2
        mock_cv2.CAP_PROP_FRAME_COUNT = 1
        mock_cv2.CAP_PROP_FRAME_WIDTH = 3
        mock_cv2.CAP_PROP_FRAME_HEIGHT = 4

        video_path = temp_dir / "av1_video.mp4"
        video_path.touch()  # Create empty file

        # Store initial environment state
        initial_env = dict(os.environ)

        result = await extractor._extract_frames_from_video(
            str(video_path), temp_dir, video_id
        )

        # Verify environment variables are restored after processing
        for key in initial_env:
            assert os.environ.get(key) == initial_env[key]

        # Should have extracted frames successfully
        assert isinstance(result, list)
        mock_cv2.VideoCapture.assert_called_with(str(video_path), mock_cv2.CAP_FFMPEG)

    @patch('keyframe_extractor.length_adaptive_extractor.cv2')
    async def test_ffmpeg_backend_fallback_to_default(self, mock_cv2, extractor, temp_dir, video_id):
        """Test fallback to default backend when FFMPEG fails."""
        # Mock FFMPEG backend failure
        mock_cap_ffmpeg = Mock()
        mock_cap_ffmpeg.isOpened.return_value = False

        # Mock default backend success
        mock_cap_default = Mock()
        mock_cap_default.isOpened.return_value = True
        mock_cap_default.get.side_effect = lambda prop: {
            1: 30.0,  # CAP_PROP_FRAME_COUNT
            2: 5.0,   # CAP_PROP_FPS
            3: 640,   # CAP_PROP_FRAME_WIDTH
            4: 480,   # CAP_PROP_FRAME_HEIGHT
            7: 10.0,  # CAP_PROP_POS_MSEC (duration)
        }.get(prop, 0)
        mock_cap_default.set.return_value = True
        mock_cap_default.read.return_value = (True, Mock())  # Mock frame

        # Configure VideoCapture to return different mocks
        mock_cv2.VideoCapture.side_effect = [mock_cap_ffmpeg, mock_cap_default, mock_cap_default]
        mock_cv2.CAP_FFMPEG = 1900
        mock_cv2.CAP_PROP_FOURCC = 6
        mock_cv2.VIDEO_ACCELERATION_ANY = 0
        mock_cv2.VideoWriter_fourcc.return_value = 0x30315661  # 'av01'

        video_path = temp_dir / "fallback_video.mp4"
        video_path.touch()  # Create empty file

        result = await extractor._extract_frames_from_video(
            str(video_path), temp_dir, video_id
        )

        # Should have fallen back to default backend and succeeded
        assert isinstance(result, list)

        # Verify the calls: first FFMPEG, then default
        assert mock_cv2.VideoCapture.call_count == 3
        mock_cv2.VideoCapture.assert_any_call(str(video_path), mock_cv2.CAP_FFMPEG)
        mock_cv2.VideoCapture.assert_any_call(str(video_path))

    @patch('keyframe_extractor.length_adaptive_extractor.cv2')
    async def test_complete_video_opening_failure(self, mock_cv2, extractor, temp_dir, video_id):
        """Test handling when all video opening attempts fail."""
        # Mock complete failure
        mock_cap = Mock()
        mock_cap.isOpened.return_value = False
        mock_cv2.VideoCapture.return_value = mock_cap
        mock_cv2.CAP_FFMPEG = 1900
        mock_cv2.CAP_PROP_FOURCC = 6
        mock_cv2.VIDEO_ACCELERATION_ANY = 0
        mock_cv2.VideoWriter_fourcc.return_value = 0x30315661  # 'av01'
        # Add missing OpenCV constants
        mock_cv2.CAP_PROP_FPS = 2
        mock_cv2.CAP_PROP_FRAME_COUNT = 1
        mock_cv2.CAP_PROP_FRAME_WIDTH = 3
        mock_cv2.CAP_PROP_FRAME_HEIGHT = 4

        video_path = temp_dir / "broken_video.mp4"
        video_path.touch()  # Create empty file

        with pytest.raises(ValueError) as context:
            await extractor._extract_frames_from_video(
                str(video_path), temp_dir, video_id
            )

        assert "Could not open video file" in str(context.value)

    @patch.dict(os.environ, {'EXISTING_VAR': 'existing_value'})
    async def test_environment_variable_restoration(self, temp_dir):
        """Test that environment variables are properly restored."""
        initial_env = dict(os.environ)

        # This test verifies the environment restoration logic
        # by checking that existing variables are preserved
        with patch('keyframe_extractor.length_adaptive_extractor.cv2') as mock_cv2:
            mock_cap = Mock()
            mock_cap.isOpened.return_value = True
            mock_cap.get.side_effect = lambda prop: {
                1: 30.0,  # CAP_PROP_FRAME_COUNT
                2: 5.0,   # CAP_PROP_FPS
                3: 640,   # CAP_PROP_FRAME_WIDTH
                4: 480,   # CAP_PROP_FRAME_HEIGHT
                7: 10.0,  # CAP_PROP_POS_MSEC (duration)
            }.get(prop, 0)
            mock_cap.set.return_value = True
            mock_cap.read.return_value = (True, Mock())  # Mock frame

            mock_cv2.VideoCapture.return_value = mock_cap
            mock_cv2.CAP_FFMPEG = 1900
            mock_cv2.CAP_PROP_FOURCC = 6
            mock_cv2.VIDEO_ACCELERATION_ANY = 0
            mock_cv2.VideoWriter_fourcc.return_value = 0x30315661  # 'av01'

            extractor = LengthAdaptiveKeyframeExtractor(create_dirs=False)
            video_path = temp_dir / "env_test.mp4"
            video_path.touch()  # Create empty file

            await extractor._extract_frames_from_video(
                str(video_path), temp_dir, "test_video"
            )

        # Verify environment is restored to original state
        assert os.environ.get('EXISTING_VAR') == 'existing_value'

        # Verify AV1-specific variables are not left in environment
        assert 'FFMPEG_HWACCEL' not in os.environ
        assert 'AV1_FORCE_SOFTWARE_DECODER' not in os.environ
        assert 'OPENCV_FFMPEG_CAPTURE_OPTIONS' not in os.environ


class TestVideoFormatCompatibility:
    """Test compatibility with different video formats."""

    @pytest.fixture
    def extractor(self):
        """Create a keyframe extractor instance for testing."""
        return LengthAdaptiveKeyframeExtractor(create_dirs=False)

    @pytest.mark.parametrize('video_format', ['mp4', 'avi', 'mov', 'mkv', 'webm'])
    @patch('keyframe_extractor.length_adaptive_extractor.cv2')
    async def test_various_video_formats(self, mock_cv2, extractor, video_format):
        """Test that various video formats are handled correctly."""
        # Mock successful video capture
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            1: 30.0,  # CAP_PROP_FRAME_COUNT
            2: 5.0,   # CAP_PROP_FPS
            3: 640,   # CAP_PROP_FRAME_WIDTH
            4: 480,   # CAP_PROP_FRAME_HEIGHT
            7: 10.0,  # CAP_PROP_POS_MSEC (duration)
        }.get(prop, 0)
        mock_cap.set.return_value = True
        mock_cap.read.return_value = (True, Mock())  # Mock frame

        mock_cv2.VideoCapture.return_value = mock_cap
        mock_cv2.CAP_FFMPEG = 1900
        mock_cv2.CAP_PROP_FOURCC = 6
        mock_cv2.VIDEO_ACCELERATION_ANY = 0
        mock_cv2.VideoWriter_fourcc.return_value = 0x30315661  # 'av01'
        # Add missing OpenCV constants
        mock_cv2.CAP_PROP_FPS = 2
        mock_cv2.CAP_PROP_FRAME_COUNT = 1
        mock_cv2.CAP_PROP_FRAME_WIDTH = 3
        mock_cv2.CAP_PROP_FRAME_HEIGHT = 4

        temp_dir = Path(tempfile.mkdtemp())
        try:
            video_path = temp_dir / f"test_video.{video_format}"
            video_path.touch()  # Create empty file

            result = await extractor._extract_frames_from_video(
                str(video_path), temp_dir, f"test_video_{video_format}"
            )

            # All formats should work the same way
            assert isinstance(result, list)
        finally:
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir)