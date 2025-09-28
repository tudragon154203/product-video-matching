"""
Unit tests for product utility functions.
"""
from utils.product_utils import select_primary_images
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
pytestmark = pytest.mark.unit


class TestSelectPrimaryImages:
    """Test cases for the select_primary_images function."""

    @pytest.mark.asyncio
    async def test_no_images(self):
        """Test when no images are available."""
        product_image_crud = MagicMock()
        product_image_crud.list_product_images = AsyncMock(return_value=[])

        result = await select_primary_images("product-123", product_image_crud, "/app/data")

        assert result == (None, 0)

    @pytest.mark.asyncio
    async def test_single_image_selection(self):
        """Test selecting a single image."""
        product_image_crud = MagicMock()

        images = [
            MagicMock(
                img_id="img-1",
                local_path="/app/data/images/img-1.jpg",
                updated_at=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
            )
        ]

        product_image_crud.list_product_images = AsyncMock(return_value=images)

        result = await select_primary_images("product-123", product_image_crud, "/app/data")

        assert result == (
            "/files/images/img-1.jpg",
            1
        )

    @pytest.mark.asyncio
    async def test_invalid_paths_return_none(self):
        """Test when all image paths are invalid."""
        product_image_crud = MagicMock()

        images = [
            MagicMock(
                img_id="img-1",
                local_path="/invalid/path/img-1.jpg",
                updated_at=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
            )
        ]

        product_image_crud.list_product_images = AsyncMock(return_value=images)

        result = await select_primary_images("product-123", product_image_crud, "/app/data")

        assert result == (None, 1)  # Count should still be 1

    @pytest.mark.asyncio
    async def test_tie_breaking_by_updated_at(self):
        """Test tie-breaking by newest updated_at."""
        product_image_crud = MagicMock()

        images = [
            MagicMock(
                img_id="img-1",
                local_path="/app/data/images/img-1.jpg",
                updated_at=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
            ),
            MagicMock(
                img_id="img-2",
                local_path="/app/data/images/img-2.jpg",
                updated_at=datetime(2024, 1, 15, 10, 35,
                                    tzinfo=timezone.utc)  # Newer
            )
        ]

        product_image_crud.list_product_images = AsyncMock(return_value=images)

        result = await select_primary_images("product-123", product_image_crud, "/app/data")

        # Should prefer newer image
        assert result[0] == "/files/images/img-2.jpg"

    @pytest.mark.asyncio
    async def test_tie_breaking_by_img_id(self):
        """Test tie-breaking by lowest img_id."""
        product_image_crud = MagicMock()

        images = [
            MagicMock(
                img_id="img-2",
                local_path="/app/data/images/img-2.jpg",
                updated_at=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
            ),
            MagicMock(
                img_id="img-1",
                local_path="/app/data/images/img-1.jpg",
                updated_at=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
            )
        ]

        product_image_crud.list_product_images = AsyncMock(return_value=images)

        result = await select_primary_images("product-123", product_image_crud, "/app/data")

        # Should prefer lower img_id
        assert result[0] == "/files/images/img-1.jpg"

    @pytest.mark.asyncio
    async def test_no_valid_paths(self):
        """Test when no valid paths are found among multiple images."""
        product_image_crud = MagicMock()

        images = [
            MagicMock(img_id="img-1", local_path="/invalid/path/img-1.jpg",
                      updated_at=datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)),
            MagicMock(img_id="img-2", local_path="/another/invalid/path/img-2.jpg",
                      updated_at=datetime(2024, 1, 15, 10, 5, tzinfo=timezone.utc)),
        ]

        product_image_crud.list_product_images = AsyncMock(return_value=images)

        result = await select_primary_images("product-123", product_image_crud, "/app/data")
        assert result == (None, 2)
