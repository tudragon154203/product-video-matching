"""Tests for CLIP processor functionality."""

from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest


pytestmark = pytest.mark.unit


class TestCLIPProcessor:
    """Test CLIP processor operations."""

    @pytest.fixture
    def mock_clip_processor(self):
        """Create mock CLIP processor."""
        with patch(
            "embedding_components.clip_processor.CLIPProcessor"
        ) as mock_processor:
            instance = Mock()
            instance.initialize = AsyncMock()
            instance.extract_clip_embeddings = AsyncMock(
                return_value=(np.array([0.1, 0.2, 0.3]), np.array([0.4, 0.5, 0.6]))
            )
            instance.cleanup = AsyncMock()
            mock_processor.return_value = instance
            return instance

    @pytest.mark.asyncio
    async def test_clip_processor_initialization(self, mock_clip_processor):
        """Test CLIP processor initialization."""
        await mock_clip_processor.initialize()
        mock_clip_processor.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_clip_processor_extract_embeddings(
        self, mock_clip_processor
    ):
        """Test CLIP processor embedding extraction."""
        from PIL import Image

        test_image = Image.new('RGB', (64, 64))
        rgb_embedding, gray_embedding = await mock_clip_processor.extract_clip_embeddings(
            test_image
        )

        mock_clip_processor.extract_clip_embeddings.assert_called_once_with(
            test_image
        )
        assert rgb_embedding is not None
        assert gray_embedding is not None
        assert len(rgb_embedding) == 3  # Should return 3D vector
        assert len(gray_embedding) == 3  # Should return 3D vector

    @pytest.mark.asyncio
    async def test_clip_processor_cleanup(self, mock_clip_processor):
        """Test CLIP processor cleanup."""
        await mock_clip_processor.cleanup()
        mock_clip_processor.cleanup.assert_called_once()
