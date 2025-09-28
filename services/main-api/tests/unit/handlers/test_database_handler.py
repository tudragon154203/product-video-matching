from handlers.database_handler import DatabaseHandler
from unittest.mock import AsyncMock, Mock
import asyncio
import pytest
pytestmark = pytest.mark.unit


class TestDatabaseHandler:
    """Test the DatabaseHandler methods"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database"""
        return Mock()

    @pytest.fixture
    def db_handler(self, mock_db):
        """Create a DatabaseHandler instance with mocked database"""
        return DatabaseHandler(mock_db)

    @pytest.mark.asyncio
    async def test_get_job_asset_types_with_images_and_videos(self, db_handler):
        """Test get_job_asset_types when job has both images and videos"""
        job_id = "test-job-123"

        # Mock the database responses
        db_handler.get_job_counts = AsyncMock(return_value=(
            5, 3, 10))  # 5 products, 3 videos, 10 matches
        # 5 products with features, 3 videos with features
        db_handler.get_features_counts = AsyncMock(return_value=(5, 3))

        asset_types = await db_handler.get_job_asset_types(job_id)

        assert asset_types["images"] is True
        assert asset_types["videos"] is True

    @pytest.mark.asyncio
    async def test_get_job_asset_types_images_only(self, db_handler):
        """Test get_job_asset_types when job has only images"""
        job_id = "images-only-job"

        # Mock the database responses
        db_handler.get_job_counts = AsyncMock(
            return_value=(5, 0, 0))  # 5 products, 0 videos, 0 matches
        # 5 products with features, 0 videos with features
        db_handler.get_features_counts = AsyncMock(return_value=(5, 0))

        asset_types = await db_handler.get_job_asset_types(job_id)

        assert asset_types["images"] is True
        assert asset_types["videos"] is False

    @pytest.mark.asyncio
    async def test_get_job_asset_types_videos_only(self, db_handler):
        """Test get_job_asset_types when job has only videos"""
        job_id = "videos-only-job"

        # Mock the database responses
        db_handler.get_job_counts = AsyncMock(
            return_value=(0, 3, 0))  # 0 products, 3 videos, 0 matches
        # 0 products with features, 3 videos with features
        db_handler.get_features_counts = AsyncMock(return_value=(0, 3))

        asset_types = await db_handler.get_job_asset_types(job_id)

        assert asset_types["images"] is False
        assert asset_types["videos"] is True

    @pytest.mark.asyncio
    async def test_get_job_asset_types_no_assets(self, db_handler):
        """Test get_job_asset_types when job has no assets"""
        job_id = "no-assets-job"

        # Mock the database responses
        db_handler.get_job_counts = AsyncMock(
            return_value=(0, 0, 0))  # 0 products, 0 videos, 0 matches
        # 0 products with features, 0 videos with features
        db_handler.get_features_counts = AsyncMock(return_value=(0, 0))

        asset_types = await db_handler.get_job_asset_types(job_id)

        assert asset_types["images"] is False
        assert asset_types["videos"] is False

    @pytest.mark.asyncio
    async def test_get_job_asset_types_database_error_fallback(self, db_handler):
        """Test get_job_asset_types falls back to default when database error occurs"""
        job_id = "error-job"

        # Mock the database responses to raise an exception
        db_handler.get_job_counts = AsyncMock(
            side_effect=Exception("Database error"))

        asset_types = await db_handler.get_job_asset_types(job_id)

        # Should fall back to default behavior (both True)
        assert asset_types["images"] is True
        assert asset_types["videos"] is True
