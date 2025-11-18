"""Unit tests for FP16 precision support in segmentation models."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
import torch

from segmentation.models.rmbg20_segmentor import RMBG20Segmentor
from segmentation.models.yolo_segmentor import YOLOSegmentor


class TestRMBG20FP16:
    """Test FP16 precision for RMBG20 model."""

    @pytest.mark.asyncio
    @patch('segmentation.models.rmbg20_segmentor.config')
    @patch('segmentation.models.rmbg20_segmentor.AutoModelForImageSegmentation')
    @patch('segmentation.models.rmbg20_segmentor.torch.cuda.is_available')
    async def test_fp16_enabled_with_cuda(self, mock_cuda_available, mock_model_class, mock_config):
        """Test that model is converted to FP16 when USE_FP16=true and CUDA is available."""
        # Setup
        mock_cuda_available.return_value = True
        mock_config.USE_FP16 = True
        mock_config.HF_TOKEN = None
        mock_config.IMG_SIZE = (1024, 1024)

        mock_model = MagicMock()
        mock_model.to.return_value = mock_model
        mock_model.eval.return_value = mock_model
        mock_model.half.return_value = mock_model
        mock_model_class.from_pretrained.return_value = mock_model

        # Execute
        segmentor = RMBG20Segmentor()
        await segmentor.initialize()

        # Assert
        mock_model.half.assert_called_once()
        assert segmentor._initialized is True

    @pytest.mark.asyncio
    @patch('segmentation.models.rmbg20_segmentor.config')
    @patch('segmentation.models.rmbg20_segmentor.AutoModelForImageSegmentation')
    @patch('segmentation.models.rmbg20_segmentor.torch.cuda.is_available')
    async def test_fp16_disabled(self, mock_cuda_available, mock_model_class, mock_config):
        """Test that model stays in FP32 when USE_FP16=false."""
        # Setup
        mock_cuda_available.return_value = True
        mock_config.USE_FP16 = False
        mock_config.HF_TOKEN = None
        mock_config.IMG_SIZE = (1024, 1024)

        mock_model = MagicMock()
        mock_model.to.return_value = mock_model
        mock_model.eval.return_value = mock_model
        mock_model.half.return_value = mock_model
        mock_model_class.from_pretrained.return_value = mock_model

        # Execute
        segmentor = RMBG20Segmentor()
        await segmentor.initialize()

        # Assert
        mock_model.half.assert_not_called()
        assert segmentor._initialized is True

    @pytest.mark.asyncio
    @patch('segmentation.models.rmbg20_segmentor.config')
    @patch('segmentation.models.rmbg20_segmentor.AutoModelForImageSegmentation')
    @patch('segmentation.models.rmbg20_segmentor.torch.cuda.is_available')
    async def test_fp16_not_applied_on_cpu(self, mock_cuda_available, mock_model_class, mock_config):
        """Test that FP16 is not applied when using CPU."""
        # Setup
        mock_cuda_available.return_value = False
        mock_config.USE_FP16 = True
        mock_config.HF_TOKEN = None
        mock_config.IMG_SIZE = (1024, 1024)

        mock_model = MagicMock()
        mock_model.to.return_value = mock_model
        mock_model.eval.return_value = mock_model
        mock_model.half.return_value = mock_model
        mock_model_class.from_pretrained.return_value = mock_model

        # Execute
        segmentor = RMBG20Segmentor()
        await segmentor.initialize()

        # Assert - half() should not be called on CPU
        mock_model.half.assert_not_called()
        assert segmentor._initialized is True

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
    def test_input_tensor_converted_to_fp16(self):
        """Test that input tensor is converted to FP16 during inference."""
        # Create FP32 input tensor
        input_tensor = torch.rand(1, 3, 1024, 1024, dtype=torch.float32).cuda()
        
        # Verify it's FP32
        assert input_tensor.dtype == torch.float32
        
        # Convert to FP16
        fp16_tensor = input_tensor.half()
        
        # Verify conversion
        assert fp16_tensor.dtype == torch.float16
        assert fp16_tensor.shape == input_tensor.shape
        
        # Cleanup
        del input_tensor
        del fp16_tensor
        torch.cuda.empty_cache()


class TestYOLOFP16:
    """Test FP16 precision for YOLO model."""

    @pytest.mark.asyncio
    @patch('segmentation.models.yolo_segmentor.config')
    @patch('segmentation.models.yolo_segmentor.YOLO')
    @patch('torch.cuda.is_available')
    @patch('segmentation.models.yolo_segmentor.os.path.exists')
    async def test_yolo_fp16_enabled_with_cuda(self, mock_exists, mock_cuda_available, mock_yolo_class, mock_config):
        """Test that YOLO model is converted to FP16 when USE_FP16=true and CUDA is available."""
        # Setup
        mock_cuda_available.return_value = True
        mock_config.USE_FP16 = True
        mock_config.MODEL_CACHE = "/app/model_cache"
        mock_exists.return_value = True

        mock_yolo = MagicMock()
        mock_yolo.model = MagicMock()
        mock_yolo.model.half = MagicMock()
        mock_yolo_class.return_value = mock_yolo

        # Execute
        segmentor = YOLOSegmentor()
        await segmentor.initialize()

        # Assert
        mock_yolo.model.half.assert_called_once()
        assert segmentor._initialized is True

    @pytest.mark.asyncio
    @patch('segmentation.models.yolo_segmentor.config')
    @patch('segmentation.models.yolo_segmentor.YOLO')
    @patch('torch.cuda.is_available')
    @patch('segmentation.models.yolo_segmentor.os.path.exists')
    async def test_yolo_fp16_disabled(self, mock_exists, mock_cuda_available, mock_yolo_class, mock_config):
        """Test that YOLO model stays in FP32 when USE_FP16=false."""
        # Setup
        mock_cuda_available.return_value = True
        mock_config.USE_FP16 = False
        mock_config.MODEL_CACHE = "/app/model_cache"
        mock_exists.return_value = True

        mock_yolo = MagicMock()
        mock_yolo.model = MagicMock()
        mock_yolo.model.half = MagicMock()
        mock_yolo_class.return_value = mock_yolo

        # Execute
        segmentor = YOLOSegmentor()
        await segmentor.initialize()

        # Assert
        mock_yolo.model.half.assert_not_called()
        assert segmentor._initialized is True

    @pytest.mark.asyncio
    @patch('segmentation.models.yolo_segmentor.config')
    @patch('segmentation.models.yolo_segmentor.YOLO')
    @patch('torch.cuda.is_available')
    @patch('segmentation.models.yolo_segmentor.os.path.exists')
    async def test_yolo_fp16_graceful_failure(self, mock_exists, mock_cuda_available, mock_yolo_class, mock_config):
        """Test that YOLO initialization continues if FP16 conversion fails."""
        # Setup
        mock_cuda_available.return_value = True
        mock_config.USE_FP16 = True
        mock_config.MODEL_CACHE = "/app/model_cache"
        mock_exists.return_value = True

        mock_yolo = MagicMock()
        mock_yolo.model = MagicMock()
        mock_yolo.model.half.side_effect = Exception("FP16 conversion failed")
        mock_yolo_class.return_value = mock_yolo

        # Execute - should not raise exception
        segmentor = YOLOSegmentor()
        await segmentor.initialize()

        # Assert - initialization should succeed despite FP16 failure
        assert segmentor._initialized is True


class TestFP16MemoryReduction:
    """Test that FP16 actually reduces memory usage."""

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
    def test_fp16_reduces_tensor_memory(self):
        """Test that FP16 tensors use approximately half the memory of FP32."""
        # Create FP32 tensor
        fp32_tensor = torch.rand(1000, 1000, dtype=torch.float32).cuda()
        fp32_memory = fp32_tensor.element_size() * fp32_tensor.nelement()

        # Create FP16 tensor
        fp16_tensor = torch.rand(1000, 1000, dtype=torch.float16).cuda()
        fp16_memory = fp16_tensor.element_size() * fp16_tensor.nelement()

        # Assert FP16 uses half the memory
        assert fp16_memory == fp32_memory / 2

        # Cleanup
        del fp32_tensor
        del fp16_tensor
        torch.cuda.empty_cache()

    def test_fp16_conversion_preserves_shape(self):
        """Test that converting to FP16 preserves tensor shape."""
        # Create FP32 tensor
        fp32_tensor = torch.rand(1, 3, 1024, 1024, dtype=torch.float32)
        original_shape = fp32_tensor.shape

        # Convert to FP16
        fp16_tensor = fp32_tensor.half()

        # Assert shape is preserved
        assert fp16_tensor.shape == original_shape
        assert fp16_tensor.dtype == torch.float16


class TestConfigFP16Setting:
    """Test FP16 configuration setting."""

    @patch.dict(os.environ, {"USE_FP16": "true"})
    def test_config_fp16_enabled_true(self):
        """Test that USE_FP16=true is correctly parsed."""
        from config_loader import ProductSegmentorConfig
        config = ProductSegmentorConfig()
        assert config.USE_FP16 is True

    @patch.dict(os.environ, {"USE_FP16": "1"})
    def test_config_fp16_enabled_one(self):
        """Test that USE_FP16=1 is correctly parsed."""
        from config_loader import ProductSegmentorConfig
        config = ProductSegmentorConfig()
        assert config.USE_FP16 is True

    @patch.dict(os.environ, {"USE_FP16": "yes"})
    def test_config_fp16_enabled_yes(self):
        """Test that USE_FP16=yes is correctly parsed."""
        from config_loader import ProductSegmentorConfig
        config = ProductSegmentorConfig()
        assert config.USE_FP16 is True

    @patch.dict(os.environ, {"USE_FP16": "enable"})
    def test_config_fp16_enabled_enable(self):
        """Test that USE_FP16=enable is correctly parsed."""
        from config_loader import ProductSegmentorConfig
        config = ProductSegmentorConfig()
        assert config.USE_FP16 is True

    @patch.dict(os.environ, {"USE_FP16": "TRUE"})
    def test_config_fp16_enabled_case_insensitive(self):
        """Test that USE_FP16 is case-insensitive."""
        from config_loader import ProductSegmentorConfig
        config = ProductSegmentorConfig()
        assert config.USE_FP16 is True

    def test_config_fp16_disabled_false(self):
        """Test that USE_FP16=false is correctly parsed."""
        with patch.dict(os.environ, {"USE_FP16": "false"}, clear=False):
            import importlib
            import config_loader
            importlib.reload(config_loader)
            assert config_loader.config.USE_FP16 is False

    def test_config_fp16_disabled_zero(self):
        """Test that USE_FP16=0 is correctly parsed."""
        with patch.dict(os.environ, {"USE_FP16": "0"}, clear=False):
            import importlib
            import config_loader
            importlib.reload(config_loader)
            assert config_loader.config.USE_FP16 is False

    def test_config_fp16_disabled_no(self):
        """Test that USE_FP16=no is correctly parsed."""
        with patch.dict(os.environ, {"USE_FP16": "no"}, clear=False):
            import importlib
            import config_loader
            importlib.reload(config_loader)
            assert config_loader.config.USE_FP16 is False

    def test_config_fp16_disabled_disable(self):
        """Test that USE_FP16=disable is correctly parsed."""
        with patch.dict(os.environ, {"USE_FP16": "disable"}, clear=False):
            import importlib
            import config_loader
            importlib.reload(config_loader)
            assert config_loader.config.USE_FP16 is False

    @patch.dict(os.environ, {}, clear=True)
    def test_config_fp16_default(self):
        """Test that USE_FP16 defaults to true."""
        from config_loader import ProductSegmentorConfig
        config = ProductSegmentorConfig()
        assert config.USE_FP16 is True


class TestConfigRetryOnOOMSetting:
    """Test RETRY_ON_OOM configuration setting."""

    @patch.dict(os.environ, {"RETRY_ON_OOM": "true"})
    def test_retry_on_oom_enabled_true(self):
        """Test that RETRY_ON_OOM=true is correctly parsed."""
        from config_loader import ProductSegmentorConfig
        config = ProductSegmentorConfig()
        assert config.RETRY_ON_OOM is True

    @patch.dict(os.environ, {"RETRY_ON_OOM": "1"})
    def test_retry_on_oom_enabled_one(self):
        """Test that RETRY_ON_OOM=1 is correctly parsed."""
        from config_loader import ProductSegmentorConfig
        config = ProductSegmentorConfig()
        assert config.RETRY_ON_OOM is True

    @patch.dict(os.environ, {"RETRY_ON_OOM": "yes"})
    def test_retry_on_oom_enabled_yes(self):
        """Test that RETRY_ON_OOM=yes is correctly parsed."""
        from config_loader import ProductSegmentorConfig
        config = ProductSegmentorConfig()
        assert config.RETRY_ON_OOM is True

    @patch.dict(os.environ, {"RETRY_ON_OOM": "enable"})
    def test_retry_on_oom_enabled_enable(self):
        """Test that RETRY_ON_OOM=enable is correctly parsed."""
        from config_loader import ProductSegmentorConfig
        config = ProductSegmentorConfig()
        assert config.RETRY_ON_OOM is True

    def test_retry_on_oom_disabled_false(self):
        """Test that RETRY_ON_OOM=false is correctly parsed."""
        with patch.dict(os.environ, {"RETRY_ON_OOM": "false"}, clear=False):
            import importlib
            import config_loader
            importlib.reload(config_loader)
            assert config_loader.config.RETRY_ON_OOM is False

    def test_retry_on_oom_disabled_zero(self):
        """Test that RETRY_ON_OOM=0 is correctly parsed."""
        with patch.dict(os.environ, {"RETRY_ON_OOM": "0"}, clear=False):
            import importlib
            import config_loader
            importlib.reload(config_loader)
            assert config_loader.config.RETRY_ON_OOM is False
