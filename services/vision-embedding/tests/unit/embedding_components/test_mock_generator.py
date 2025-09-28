"""Tests for mock generator functionality."""

import pytest
pytestmark = pytest.mark.unit
from unittest.mock import Mock, patch, AsyncMock
import numpy as np


class TestMockGenerator:
    """Test mock generator operations."""
    
    @pytest.fixture
    def mock_generator(self):
        """Create mock generator."""
        with patch('embedding_components.mock_generator.MockEmbeddingGenerator') as mock_gen:
            instance = Mock()
            instance.initialize = AsyncMock()
            instance.extract_embeddings = AsyncMock(return_value=np.array([0.5, 0.5, 0.5]))
            instance.cleanup = AsyncMock()
            mock_gen.return_value = instance
            return instance
    
    @pytest.mark.asyncio
    async def test_mock_generator_initialization(self, mock_generator):
        """Test mock generator initialization."""
        await mock_generator.initialize()
        mock_generator.initialize.assert_called_once()
    
    @pytest.mark.asyncio 
    async def test_mock_generator_extract_embeddings(self, mock_generator):
        """Test mock generator embedding extraction."""
        test_image_path = "/tmp/test_image.jpg"
        embeddings = await mock_generator.extract_embeddings(test_image_path)
        
        mock_generator.extract_embeddings.assert_called_once_with(test_image_path)
        assert embeddings is not None
        assert len(embeddings) == 3  # Should return 3D vector
        # Mock generator should return consistent values
        assert np.array_equal(embeddings, np.array([0.5, 0.5, 0.5]))
    
    @pytest.mark.asyncio
    async def test_mock_generator_cleanup(self, mock_generator):
        """Test mock generator cleanup."""
        await mock_generator.cleanup()
        mock_generator.cleanup.assert_called_once()