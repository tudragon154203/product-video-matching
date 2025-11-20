"""
Integration tests for IdempotencyManager.

Tests database-level and file-level idempotency functionality.
"""

import pytest
from unittest.mock import patch, mock_open

pytestmark = pytest.mark.integration


class TestVideoIdempotency:
    """Test video-level idempotency functionality."""

    @pytest.mark.asyncio
    async def test_check_video_exists_true(self, idempotency_manager, mock_db):
        """Test checking existing video returns True."""
        # Setup mock to return existing video
        mock_db.fetch_one.return_value = {"video_id": "test_video_123", "platform": "youtube"}

        result = await idempotency_manager.check_video_exists("test_video_123", "youtube")

        assert result is True
        # Check that the actual query was called (ignoring the health check "SELECT 1")
        actual_calls = [call for call in mock_db.fetch_one.call_args_list
                       if "SELECT video_id FROM videos" in str(call)]
        assert len(actual_calls) == 1
        assert actual_calls[0] == (
            ("SELECT video_id FROM videos WHERE video_id = $1 AND platform = $2", "test_video_123", "youtube"),
        )

    @pytest.mark.asyncio
    async def test_check_video_exists_false(self, idempotency_manager, mock_db):
        """Test checking non-existent video returns False."""
        # Setup mock to return None (no existing video)
        mock_db.fetch_one.return_value = None

        result = await idempotency_manager.check_video_exists("nonexistent_video", "youtube")

        assert result is False
        # Check that fetch_one was called (includes health check + actual query)
        assert mock_db.fetch_one.call_count >= 1

    @pytest.mark.asyncio
    async def test_check_video_exists_database_error(self, idempotency_manager, mock_db):
        """Test database error handling in video existence check."""
        # Setup mock to raise exception
        mock_db.fetch_one.side_effect = Exception("Database connection failed")

        result = await idempotency_manager.check_video_exists("test_video", "youtube")

        assert result is False  # Should return False on error

    @pytest.mark.asyncio
    async def test_get_existing_video_found(self, idempotency_manager, mock_db, sample_video_data):
        """Test retrieving existing video returns video data."""
        mock_db.fetch_one.return_value = sample_video_data

        result = await idempotency_manager.get_existing_video("test_video_123", "youtube")

        assert result == sample_video_data
        # fetch_one called at least once (may include health checks)
        assert mock_db.fetch_one.call_count >= 1

    @pytest.mark.asyncio
    async def test_get_existing_video_not_found(self, idempotency_manager, mock_db):
        """Test retrieving non-existent video returns None."""
        mock_db.fetch_one.return_value = None

        result = await idempotency_manager.get_existing_video("nonexistent", "youtube")

        assert result is None

    @pytest.mark.asyncio
    async def test_create_video_with_idempotency_new(self, idempotency_manager, mock_db, sample_video_data):
        """Test creating new video with idempotency."""
        # Setup mocks for new video creation
        mock_db.fetch_one.return_value = None  # Video doesn't exist
        mock_db.execute.return_value = None

        created_new, video_id = await idempotency_manager.create_video_with_idempotency(
            video_id="new_video_123",
            platform="youtube",
            url="https://example.com/video",
            title="New Video",
            duration_s=120,
            job_id="job_123"
        )

        assert created_new is True
        assert video_id == "new_video_123"
        # execute should be called at least once for the INSERT
        assert mock_db.execute.call_count >= 1

        # Verify the INSERT query contains ON CONFLICT clause
        call_args = mock_db.execute.call_args[0]
        assert "ON CONFLICT" in call_args[0]

    @pytest.mark.asyncio
    async def test_create_video_with_idempotency_existing(self, idempotency_manager, mock_db, sample_video_data):
        """Test handling existing video with idempotency."""
        # Setup mocks for existing video
        existing_video = {"video_id": "existing_video", "platform": "youtube"}
        mock_db.fetch_one.return_value = existing_video

        created_new, video_id = await idempotency_manager.create_video_with_idempotency(
            video_id="existing_video",
            platform="youtube",
            url="https://example.com/video",
            title="Existing Video"
        )

        assert created_new is False
        assert video_id == "existing_video"
        # execute should not be called for existing video
        mock_db.execute.assert_not_called()


class TestFrameIdempotency:
    """Test frame-level idempotency functionality."""

    @pytest.mark.asyncio
    async def test_check_frame_exists_true(self, idempotency_manager, mock_db):
        """Test checking existing frame returns True."""
        mock_db.fetch_one.return_value = {"frame_id": "test_video_frame_0"}

        result = await idempotency_manager.check_frame_exists("test_video", 0)

        assert result is True
        mock_db.fetch_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_frame_exists_false(self, idempotency_manager, mock_db):
        """Test checking non-existent frame returns False."""
        mock_db.fetch_one.return_value = None

        result = await idempotency_manager.check_frame_exists("test_video", 99)

        assert result is False

    @pytest.mark.asyncio
    async def test_create_frame_with_idempotency_new(self, idempotency_manager, mock_db):
        """Test creating new frame with idempotency."""
        # First call: frame doesn't exist, Second call: video exists
        mock_db.fetch_one.side_effect = [None, {"video_id": "test_video"}]

        created_new, frame_id = await idempotency_manager.create_frame_with_idempotency(
            video_id="test_video",
            frame_index=0,
            timestamp=0.0,
            local_path="/path/to/frame.jpg"
        )

        assert created_new is True
        assert frame_id == "test_video_frame_0"
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_frame_with_idempotency_existing(self, idempotency_manager, mock_db):
        """Test handling existing frame with idempotency."""
        existing_frame = {"frame_id": "test_video_frame_0"}
        mock_db.fetch_one.return_value = existing_frame

        created_new, frame_id = await idempotency_manager.create_frame_with_idempotency(
            video_id="test_video",
            frame_index=0,
            timestamp=0.0,
            local_path="/path/to/frame.jpg"
        )

        assert created_new is False
        assert frame_id == "test_video_frame_0"
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_existing_frames(self, idempotency_manager, mock_db, sample_keyframes):
        """Test retrieving existing frames for video."""
        mock_frames = [
            {"frame_id": "test_video_frame_0", "ts": 0.0, "local_path": "/path/frame_0.jpg"},
            {"frame_id": "test_video_frame_1", "ts": 5.0, "local_path": "/path/frame_1.jpg"}
        ]
        mock_db.fetch_all.return_value = mock_frames

        result = await idempotency_manager.get_existing_frames("test_video")

        assert len(result) == 2
        assert result[0]["frame_id"] == "test_video_frame_0"
        assert result[1]["ts"] == 5.0
        mock_db.fetch_all.assert_called_once()


class TestFileContentIdempotency:
    """Test file content-level idempotency."""

    @pytest.mark.asyncio
    @patch('builtins.open', new_callable=mock_open, read_data=b"test video content")
    @patch('pathlib.Path.exists', return_value=True)
    async def test_check_file_content_processed_true(self, mock_exists, mock_file, idempotency_manager, mock_db):
        """Test checking processed file content returns True."""
        mock_db.fetch_one.return_value = {"file_hash": "abc123"}

        result = await idempotency_manager.check_file_content_processed("/path/to/video.mp4")

        assert result is True
        mock_db.fetch_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_file_content_processed_false(self, idempotency_manager, mock_db):
        """Test checking unprocessed file content returns False."""
        mock_db.fetch_one.return_value = None

        result = await idempotency_manager.check_file_content_processed("/path/to/video.mp4")

        assert result is False

    @pytest.mark.asyncio
    async def test_check_file_content_processed_nonexistent_file(self, idempotency_manager):
        """Test checking non-existent file returns False."""
        result = await idempotency_manager.check_file_content_processed("/nonexistent/file.mp4")

        assert result is False

    @pytest.mark.asyncio
    @patch('builtins.open', new_callable=mock_open, read_data=b"test video content")
    @patch('pathlib.Path.exists', return_value=True)
    async def test_mark_file_content_processed_success(self, mock_exists, mock_file, idempotency_manager, mock_db):
        """Test successfully marking file content as processed."""
        result = await idempotency_manager.mark_file_content_processed("/path/to/video.mp4")

        assert result is True
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_file_content_processed_nonexistent_file(self, idempotency_manager):
        """Test marking non-existent file returns False."""
        result = await idempotency_manager.mark_file_content_processed("/nonexistent/file.mp4")

        assert result is False
        # Database should not be called for non-existent file
        idempotency_manager.db.execute.assert_not_called()


class TestFileHashCalculation:
    """Test file hash calculation functionality."""

    def test_calculate_file_hash_success(self, idempotency_manager, temp_video_file):
        """Test successful file hash calculation."""
        hash_result = idempotency_manager.calculate_file_hash(temp_video_file)

        assert isinstance(hash_result, str)
        assert len(hash_result) == 64  # SHA-256 produces 64 character hex string
        assert hash_result != ""

    def test_calculate_file_hash_nonexistent_file(self, idempotency_manager):
        """Test hash calculation with non-existent file."""
        hash_result = idempotency_manager.calculate_file_hash("/nonexistent/file.mp4")

        assert hash_result == ""

    @patch('builtins.open', side_effect=PermissionError("Permission denied"))
    def test_calculate_file_hash_permission_error(self, mock_file, idempotency_manager, temp_video_file):
        """Test hash calculation with permission error."""
        hash_result = idempotency_manager.calculate_file_hash(temp_video_file)

        assert hash_result == ""


class TestIdempotencyManagerIntegration:
    """Integration tests for idempotency manager."""

    @pytest.mark.asyncio
    async def test_full_video_idempotency_workflow(self, idempotency_manager, mock_db, sample_video_data):
        """Test complete video idempotency workflow."""
        video_id = "workflow_test_video"
        platform = "youtube"

        # Step 1: Check if video exists (should not exist)
        mock_db.fetch_one.return_value = None
        exists = await idempotency_manager.check_video_exists(video_id, platform)
        assert exists is False

        # Step 2: Create new video
        created_new, returned_id = await idempotency_manager.create_video_with_idempotency(
            video_id=video_id,
            platform=platform,
            url=sample_video_data["url"],
            title=sample_video_data["title"]
        )
        assert created_new is True
        assert returned_id == video_id

        # Step 3: Check if video exists (should exist now)
        existing_video = {"video_id": video_id, "platform": platform}
        mock_db.fetch_one.return_value = existing_video
        exists = await idempotency_manager.check_video_exists(video_id, platform)
        assert exists is True

        # Step 4: Try to create same video again (should be prevented)
        created_new, returned_id = await idempotency_manager.create_video_with_idempotency(
            video_id=video_id,
            platform=platform,
            url=sample_video_data["url"],
            title=sample_video_data["title"]
        )
        assert created_new is False
        assert returned_id == video_id

    @pytest.mark.asyncio
    async def test_full_frame_idempotency_workflow(self, idempotency_manager, mock_db, sample_keyframes):
        """Test complete frame idempotency workflow."""
        video_id = "frame_workflow_test"

        # Step 1: Create frames for the first time
        for i, (timestamp, path) in enumerate(sample_keyframes):
            # Reset side_effect for each iteration: frame doesn't exist, video exists
            mock_db.fetch_one.side_effect = [None, {"video_id": video_id}]
            mock_db.execute.reset_mock()

            created_new, frame_id = await idempotency_manager.create_frame_with_idempotency(
                video_id=video_id,
                frame_index=i,
                timestamp=timestamp,
                local_path=path
            )
            assert created_new is True
            assert frame_id == f"{video_id}_frame_{i}"

        # Step 2: Try to create same frames again (should be prevented)
        for i, (timestamp, path) in enumerate(sample_keyframes):
            existing_frame = {"frame_id": f"{video_id}_frame_{i}"}
            # Reset to return_value for consistent behavior
            mock_db.fetch_one.side_effect = None
            mock_db.fetch_one.return_value = existing_frame

            created_new, frame_id = await idempotency_manager.create_frame_with_idempotency(
                video_id=video_id,
                frame_index=i,
                timestamp=timestamp,
                local_path=path
            )
            assert created_new is False
            assert frame_id == f"{video_id}_frame_{i}"

    @pytest.mark.asyncio
    async def test_error_handling_consistency(self, idempotency_manager, mock_db):
        """Test that error handling is consistent across all methods."""
        # Setup all database operations to raise exceptions
        mock_db.fetch_one.side_effect = Exception("Database error")
        mock_db.fetch_all.side_effect = Exception("Database error")
        mock_db.execute.side_effect = Exception("Database error")

        # All methods should handle errors gracefully
        video_exists = await idempotency_manager.check_video_exists("test", "platform")
        assert video_exists is False

        frame_exists = await idempotency_manager.check_frame_exists("test", 0)
        assert frame_exists is False

        existing_video = await idempotency_manager.get_existing_video("test", "platform")
        assert existing_video is None

        existing_frames = await idempotency_manager.get_existing_frames("test")
        assert existing_frames == []

        file_processed = await idempotency_manager.check_file_content_processed("/path")
        assert file_processed is False

        mark_result = await idempotency_manager.mark_file_content_processed("/path")
        assert mark_result is False

        # Creation methods should raise exceptions for database errors
        with pytest.raises(Exception):
            await idempotency_manager.create_video_with_idempotency("test", "platform", "url")

        with pytest.raises(Exception):
            await idempotency_manager.create_frame_with_idempotency("test", 0, 0.0, "/path")
