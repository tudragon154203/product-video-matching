"""
Unit tests for video utility functions.
"""
from utils.video_utils import select_preview_frame
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
pytestmark = pytest.mark.unit


class TestSelectPreviewFrame:
    """Test cases for the select_preview_frame function."""

    @pytest.mark.asyncio
    async def test_no_frames(self):
        """Test when no frames are available."""
        video_frame_crud = MagicMock()
        video_frame_crud.list_video_frames_by_video = AsyncMock(
            return_value=[])

        result = await select_preview_frame("video-123", 120.0, video_frame_crud, "/app/data")

        assert result is None

    @pytest.mark.asyncio
    async def test_prefer_segmented_frame_at_middle(self):
        """Test preferring segmented frame closest to middle timestamp."""
        video_frame_crud = MagicMock()

        # Mock frames: one segmented at middle, one raw at beginning
        frames = [
            MagicMock(
                frame_id="frame-1",
                ts=10.0,
                local_path="/app/data/videos/frames/frame-1.jpg",
                segment_local_path="/app/data/videos/masked/frame-1.jpg",
                updated_at=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
            ),
            MagicMock(
                frame_id="frame-2",
                ts=60.0,  # Middle of 120s video
                local_path="/app/data/videos/frames/frame-2.jpg",
                segment_local_path="/app/data/videos/masked/frame-2.jpg",
                updated_at=datetime(2024, 1, 15, 10, 35, tzinfo=timezone.utc)
            )
        ]

        video_frame_crud.list_video_frames_by_video = AsyncMock(
            return_value=frames)

        result = await select_preview_frame("video-123", 120.0, video_frame_crud, "/app/data")

        assert result is not None
        # Should prefer segmented frame at middle
        assert result['frame_id'] == "frame-2"
        assert result['ts'] == 60.0
        assert result['url'] == "/files/videos/frames/frame-2.jpg"
        assert result['segment_url'] == "/files/videos/masked/frame-2.jpg"

    @pytest.mark.asyncio
    async def test_fallback_to_raw_frame(self):
        """Test falling back to raw frame when no segmented frames available."""
        video_frame_crud = MagicMock()

        # Mock frames: only raw frames
        frames = [
            MagicMock(
                frame_id="frame-1",
                ts=10.0,
                local_path="/app/data/videos/frames/frame-1.jpg",
                segment_local_path=None,
                updated_at=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
            ),
            MagicMock(
                frame_id="frame-2",
                ts=60.0,
                local_path="/app/data/videos/frames/frame-2.jpg",
                segment_local_path=None,
                updated_at=datetime(2024, 1, 15, 10, 35, tzinfo=timezone.utc)
            )
        ]

        video_frame_crud.list_video_frames_by_video = AsyncMock(
            return_value=frames)

        result = await select_preview_frame("video-123", 120.0, video_frame_crud, "/app/data")

        assert result is not None
        assert result['frame_id'] == "frame-2"  # Should prefer frame at middle
        assert result['ts'] == 60.0
        assert result['url'] == "/files/videos/frames/frame-2.jpg"
        assert result['segment_url'] is None

    @pytest.mark.asyncio
    async def test_invalid_paths_return_none(self):
        """Test when all frame paths are invalid."""
        video_frame_crud = MagicMock()

        # Mock frames with invalid paths
        frames = [
            MagicMock(
                frame_id="frame-1",
                ts=60.0,
                local_path="/invalid/path/frame-1.jpg",
                segment_local_path=None,
                updated_at=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
            )
        ]

        video_frame_crud.list_video_frames_by_video = AsyncMock(
            return_value=frames)

        result = await select_preview_frame("video-123", 120.0, video_frame_crud, "/app/data")

        assert result is None

    @pytest.mark.asyncio
    async def test_tie_breaking_by_updated_at(self):
        """Test tie-breaking by newest updated_at."""
        video_frame_crud = MagicMock()

        # Mock frames at same timestamp, different update times
        frames = [
            MagicMock(
                frame_id="frame-1",
                ts=60.0,
                local_path="/app/data/videos/frames/frame-1.jpg",
                segment_local_path=None,
                updated_at=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
            ),
            MagicMock(
                frame_id="frame-2",
                ts=60.0,
                local_path="/app/data/videos/frames/frame-2.jpg",
                segment_local_path=None,
                updated_at=datetime(2024, 1, 15, 10, 35,
                                    tzinfo=timezone.utc)  # Newer
            )
        ]

        video_frame_crud.list_video_frames_by_video = AsyncMock(
            return_value=frames)

        result = await select_preview_frame("video-123", 120.0, video_frame_crud, "/app/data")

        assert result is not None
        assert result['frame_id'] == "frame-2"  # Should prefer newer frame

    @pytest.mark.asyncio
    async def test_tie_breaking_by_frame_id(self):
        """Test tie-breaking by lowest frame_id."""
        video_frame_crud = MagicMock()

        # Mock frames with same timestamp and update time
        frames = [
            MagicMock(
                frame_id="frame-2",
                ts=60.0,
                local_path="/app/data/videos/frames/frame-2.jpg",
                segment_local_path=None,
                updated_at=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
            ),
            MagicMock(
                frame_id="frame-1",
                ts=60.0,
                local_path="/app/data/videos/frames/frame-1.jpg",
                segment_local_path=None,
                updated_at=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
            )
        ]

        video_frame_crud.list_video_frames_by_video = AsyncMock(
            return_value=frames)

        result = await select_preview_frame("video-123", 120.0, video_frame_crud, "/app/data")

        assert result is not None
        assert result['frame_id'] == "frame-1"  # Should prefer lower frame_id
