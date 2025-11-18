"""Tests for device configuration (CUDA/CPU) in embedding extractor."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
import torch


pytestmark = pytest.mark.unit


class TestDeviceConfiguration:
    """Test device configuration for embedding extractor."""

    @pytest.fixture
    def mock_clip_models(self):
        """Mock CLIP model and processor loading."""
        with patch("embedding.CLIPProcessor") as mock_processor, \
             patch("embedding.CLIPModel") as mock_model:
            mock_processor_instance = Mock()
            mock_model_instance = Mock()
            mock_model_instance.to = Mock(return_value=mock_model_instance)
            mock_model_instance.eval = Mock(return_value=mock_model_instance)
            
            mock_processor.from_pretrained = Mock(return_value=mock_processor_instance)
            mock_model.from_pretrained = Mock(return_value=mock_model_instance)
            
            yield {
                "processor": mock_processor,
                "model": mock_model,
                "processor_instance": mock_processor_instance,
                "model_instance": mock_model_instance
            }

    @pytest.mark.asyncio
    async def test_device_cuda_when_available(self, mock_clip_models):
        """Test that CUDA device is used when DEVICE=cuda and CUDA is available."""
        with patch("embedding.config.DEVICE", "cuda"), \
             patch("embedding.torch.cuda.is_available", return_value=True):
            from embedding import EmbeddingExtractor
            extractor = EmbeddingExtractor()
            await extractor.initialize()
            
            assert extractor.device == torch.device("cuda")
            mock_clip_models["model_instance"].to.assert_called_once_with(torch.device("cuda"))

    @pytest.mark.asyncio
    async def test_device_cpu_when_cuda_unavailable(self, mock_clip_models):
        """Test that CPU device is used when DEVICE=cuda but CUDA is unavailable."""
        with patch("embedding.config.DEVICE", "cuda"), \
             patch("embedding.torch.cuda.is_available", return_value=False):
            from embedding import EmbeddingExtractor
            extractor = EmbeddingExtractor()
            await extractor.initialize()
            
            assert extractor.device == torch.device("cpu")
            mock_clip_models["model_instance"].to.assert_called_once_with(torch.device("cpu"))

    @pytest.mark.asyncio
    async def test_device_cpu_when_configured(self, mock_clip_models):
        """Test that CPU device is used when DEVICE=cpu regardless of CUDA availability."""
        with patch("embedding.config.DEVICE", "cpu"), \
             patch("embedding.torch.cuda.is_available", return_value=True):  # CUDA available but not requested
            from embedding import EmbeddingExtractor
            extractor = EmbeddingExtractor()
            await extractor.initialize()
            
            assert extractor.device == torch.device("cpu")
            mock_clip_models["model_instance"].to.assert_called_once_with(torch.device("cpu"))

    @pytest.mark.asyncio
    async def test_device_default_cuda(self, mock_clip_models):
        """Test that CUDA is the default when DEVICE env var is not set."""
        with patch("embedding.config.DEVICE", "cuda"), \
             patch("embedding.torch.cuda.is_available", return_value=True):
            from embedding import EmbeddingExtractor
            extractor = EmbeddingExtractor()
            await extractor.initialize()
            
            assert extractor.device == torch.device("cuda")

    @pytest.mark.asyncio
    async def test_device_case_insensitive(self, mock_clip_models):
        """Test that device configuration is case-insensitive."""
        for device_value in ["CUDA", "Cuda", "CuDa"]:
            with patch("embedding.config.DEVICE", device_value), \
                 patch("embedding.torch.cuda.is_available", return_value=True):
                from embedding import EmbeddingExtractor
                extractor = EmbeddingExtractor()
                await extractor.initialize()
                
                assert extractor.device == torch.device("cuda")

    @pytest.mark.asyncio
    async def test_cleanup_clears_cuda_cache(self, mock_clip_models):
        """Test that cleanup clears CUDA cache when using GPU."""
        with patch("embedding.config.DEVICE", "cuda"), \
             patch("embedding.torch.cuda.is_available", return_value=True), \
             patch("embedding.torch.cuda.empty_cache") as mock_empty_cache:
            from embedding import EmbeddingExtractor
            extractor = EmbeddingExtractor()
            await extractor.initialize()
            await extractor.cleanup()
            
            mock_empty_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_model_loads_correct_clip_variant(self, mock_clip_models):
        """Test that the correct CLIP model is loaded based on EMBED_MODEL config."""
        with patch("embedding.config.DEVICE", "cuda"), \
             patch("embedding.torch.cuda.is_available", return_value=True):
            from embedding import EmbeddingExtractor
            extractor = EmbeddingExtractor(model_name="clip-vit-b32")
            await extractor.initialize()
            
            mock_clip_models["processor"].from_pretrained.assert_called_once_with(
                "openai/clip-vit-base-patch32"
            )
            mock_clip_models["model"].from_pretrained.assert_called_once_with(
                "openai/clip-vit-base-patch32"
            )
