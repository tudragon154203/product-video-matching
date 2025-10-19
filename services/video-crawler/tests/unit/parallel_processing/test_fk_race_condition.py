"""Unit test for foreign key race condition in video and frame creation."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from services.idempotency_manager import IdempotencyManager


class TestForeignKeyRaceCondition:
    """Test cases for the foreign key race condition fix."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database manager."""
        db = MagicMock()
        db.pool = MagicMock()
        db.fetch_one = AsyncMock()
        db.execute = AsyncMock()
        db.fetch_all = AsyncMock()
        return db

    @pytest.fixture
    def idempotency_manager(self, mock_db):
        """Create idempotency manager with mock database."""
        return IdempotencyManager(mock_db)

    @pytest.mark.asyncio
    async def test_frame_creation_fails_when_video_not_present(self, idempotency_manager, mock_db):
        """Test that frame creation raises RuntimeError when parent video doesn't exist."""
        video_id = "test_video_123"
        frame_index = 0
        timestamp = 10.0
        local_path = "/path/to/frame.jpg"

        # Mock database calls to handle both frame existence and video existence checks
        async def mock_fetch_one(query, *args):
            if "SELECT frame_id FROM video_frames" in query:
                return None  # Frame doesn't exist
            elif "SELECT video_id FROM videos" in query:
                return None  # Video doesn't exist
            return None

        mock_db.fetch_one.side_effect = mock_fetch_one

        # Test that frame creation fails
        with pytest.raises(RuntimeError, match=f"Parent video {video_id} does not exist for frame insertion"):
            await idempotency_manager.create_frame_with_idempotency(
                video_id=video_id,
                frame_index=frame_index,
                timestamp=timestamp,
                local_path=local_path
            )

        # Verify video check was called (should be the last call)
        video_check_calls = [call for call in mock_db.fetch_one.call_args_list
                           if "SELECT video_id FROM videos" in str(call)]
        assert len(video_check_calls) == 1
        assert video_check_calls[0][0][1] == video_id

        # Verify frame insertion was NOT called
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_frame_creation_succeeds_when_video_present(self, idempotency_manager, mock_db):
        """Test that frame creation succeeds when parent video exists."""
        video_id = "test_video_123"
        frame_index = 0
        timestamp = 10.0
        local_path = "/path/to/frame.jpg"

        # Mock video check to return video record
        mock_db.fetch_one.return_value = {"video_id": video_id}

        # Mock frame existence check to return False (frame doesn't exist)
        with patch.object(idempotency_manager, 'check_frame_exists', return_value=False):
            # Test that frame creation succeeds
            created_new, frame_id = await idempotency_manager.create_frame_with_idempotency(
                video_id=video_id,
                frame_index=frame_index,
                timestamp=timestamp,
                local_path=local_path
            )

            # Verify success
            assert created_new is True
            assert frame_id == f"{video_id}_frame_{frame_index}"

        # Verify video check was called
        mock_db.fetch_one.assert_called_with(
            "SELECT video_id FROM videos WHERE video_id = $1",
            video_id
        )

        # Verify frame insertion was called
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_video_and_frame_creation_race_condition(self, idempotency_manager, mock_db):
        """Test race condition where frame creation happens immediately after video creation."""
        video_id = "race_condition_video"
        platform = "youtube"
        url = "https://youtube.com/watch?v=test"
        frame_index = 0
        timestamp = 5.0
        local_path = "/path/to/frame.jpg"

        # Simulate the race condition scenario
        video_creation_calls = []
        frame_creation_calls = []

        async def mock_execute(query, *args):
            """Mock execute that tracks call order."""
            if "INSERT INTO videos" in query:
                video_creation_calls.append((query, args))
            elif "INSERT INTO video_frames" in query:
                frame_creation_calls.append((query, args))
            return "INSERT 0 1"

        async def mock_fetch_one(query, *args):
            """Mock fetch_one that simulates video visibility timing."""
            if "SELECT video_id FROM videos WHERE video_id = $1" in query:
                # Simulate slight delay before video becomes visible
                await asyncio.sleep(0.01)
                return {"video_id": video_id}
            elif "SELECT * FROM videos WHERE video_id = $1" in query:
                # For existing video check in video creation
                return None  # Video doesn't exist initially
            return None

        async def mock_check_frame_exists(video_id_param, frame_index_param):
            """Mock frame existence check."""
            return False

        mock_db.execute.side_effect = mock_execute
        mock_db.fetch_one.side_effect = mock_fetch_one

        with patch.object(idempotency_manager, 'check_frame_exists', side_effect=mock_check_frame_exists):
            # Create video and frame concurrently to simulate race condition
            video_task = asyncio.create_task(
                idempotency_manager.create_video_with_idempotency(
                    video_id=video_id,
                    platform=platform,
                    url=url
                )
            )

            # Small delay to ensure video creation starts first
            await asyncio.sleep(0.001)

            frame_task = asyncio.create_task(
                idempotency_manager.create_frame_with_idempotency(
                    video_id=video_id,
                    frame_index=frame_index,
                    timestamp=timestamp,
                    local_path=local_path
                )
            )

            # Wait for both to complete
            video_result, frame_result = await asyncio.gather(video_task, frame_task)

            # Verify both succeeded
            assert video_result == (True, video_id)  # (created_new, video_id)
            assert frame_result == (True, f"{video_id}_frame_{frame_index}")  # (created_new, frame_id)

        # Verify video creation was attempted
        assert len(video_creation_calls) == 1
        assert "INSERT INTO videos" in video_creation_calls[0][0]

        # Verify frame creation was attempted after video check
        assert len(frame_creation_calls) == 1
        assert "INSERT INTO video_frames" in frame_creation_calls[0][0]

    @pytest.mark.asyncio
    async def test_frame_idempotency_when_existing(self, idempotency_manager, mock_db):
        """Test that frame creation is idempotent when frame already exists."""
        video_id = "test_video_123"
        frame_index = 0
        timestamp = 10.0
        local_path = "/path/to/frame.jpg"

        # Mock frame existence check to return True (frame already exists)
        with patch.object(idempotency_manager, 'check_frame_exists', return_value=True):
            # Test that frame creation returns existing frame
            created_new, frame_id = await idempotency_manager.create_frame_with_idempotency(
                video_id=video_id,
                frame_index=frame_index,
                timestamp=timestamp,
                local_path=local_path
            )

            # Verify idempotency behavior
            assert created_new is False
            assert frame_id == f"{video_id}_frame_{frame_index}"

        # Verify video check was NOT called (early exit for performance)
        video_check_calls = [call for call in mock_db.fetch_one.call_args_list
                           if "SELECT video_id FROM videos" in str(call)]
        assert len(video_check_calls) == 0

        # Verify frame insertion was NOT called since frame already exists
        mock_db.execute.assert_not_called()