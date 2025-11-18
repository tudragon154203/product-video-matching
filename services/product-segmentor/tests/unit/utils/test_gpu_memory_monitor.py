"""Unit tests for GPU memory monitor."""

import pytest
from unittest.mock import patch, MagicMock
from utils.gpu_memory_monitor import GPUMemoryMonitor, clear_gpu_memory


class TestGPUMemoryMonitor:
    """Test GPU memory monitoring functionality."""

    @patch("utils.gpu_memory_monitor.torch")
    def test_initialization_with_cuda(self, mock_torch):
        """Test monitor initialization when CUDA is available."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.device_count.return_value = 1

        monitor = GPUMemoryMonitor(memory_threshold=0.85)

        assert monitor.memory_threshold == 0.85
        assert monitor.cuda_available is True
        assert monitor._cleanup_counter == 0

    @patch("utils.gpu_memory_monitor.torch")
    def test_initialization_without_cuda(self, mock_torch):
        """Test monitor initialization when CUDA is not available."""
        mock_torch.cuda.is_available.return_value = False

        monitor = GPUMemoryMonitor(memory_threshold=0.85)

        assert monitor.cuda_available is False

    @patch("utils.gpu_memory_monitor.torch")
    def test_get_memory_info_with_cuda(self, mock_torch):
        """Test getting memory info when CUDA is available."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.mem_get_info.return_value = (4 * 1024**3, 8 * 1024**3)  # 4GB free, 8GB total

        monitor = GPUMemoryMonitor()
        used_bytes, total_bytes, usage_fraction = monitor.get_memory_info()

        assert used_bytes == 4 * 1024**3  # 4GB used
        assert total_bytes == 8 * 1024**3  # 8GB total
        assert usage_fraction == 0.5  # 50% usage

    @patch("utils.gpu_memory_monitor.torch")
    def test_get_memory_info_without_cuda(self, mock_torch):
        """Test getting memory info when CUDA is not available."""
        mock_torch.cuda.is_available.return_value = False

        monitor = GPUMemoryMonitor()
        used_bytes, total_bytes, usage_fraction = monitor.get_memory_info()

        assert used_bytes == 0
        assert total_bytes == 0
        assert usage_fraction == 0.0

    @patch("utils.gpu_memory_monitor.torch")
    def test_should_block_below_threshold(self, mock_torch):
        """Test that tasks are not blocked below threshold."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.mem_get_info.return_value = (4 * 1024**3, 8 * 1024**3)  # 50% usage

        monitor = GPUMemoryMonitor(memory_threshold=0.85)
        should_block = monitor.should_block_new_task()

        assert should_block is False

    @patch("utils.gpu_memory_monitor.torch")
    def test_should_block_above_threshold(self, mock_torch):
        """Test that tasks are blocked above threshold."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.mem_get_info.return_value = (0.5 * 1024**3, 8 * 1024**3)  # 93.75% usage

        monitor = GPUMemoryMonitor(memory_threshold=0.85)
        should_block = monitor.should_block_new_task()

        assert should_block is True

    @patch("utils.gpu_memory_monitor.torch")
    def test_periodic_cleanup_on_interval(self, mock_torch):
        """Test that cleanup happens at the specified interval."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.mem_get_info.return_value = (4 * 1024**3, 8 * 1024**3)

        monitor = GPUMemoryMonitor()
        monitor._cleanup_interval = 3

        # First two calls should not trigger cleanup
        monitor.periodic_cleanup()
        assert mock_torch.cuda.empty_cache.call_count == 0

        monitor.periodic_cleanup()
        assert mock_torch.cuda.empty_cache.call_count == 0

        # Third call should trigger cleanup
        monitor.periodic_cleanup()
        assert mock_torch.cuda.empty_cache.call_count == 1
        assert mock_torch.cuda.synchronize.call_count == 1

    @patch("utils.gpu_memory_monitor.torch")
    def test_periodic_cleanup_force(self, mock_torch):
        """Test that forced cleanup happens immediately."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.mem_get_info.return_value = (4 * 1024**3, 8 * 1024**3)

        monitor = GPUMemoryMonitor()

        # Force cleanup should happen immediately
        monitor.periodic_cleanup(force=True)
        assert mock_torch.cuda.empty_cache.call_count == 1
        assert mock_torch.cuda.synchronize.call_count == 1

    @patch("utils.gpu_memory_monitor.torch")
    def test_clear_gpu_memory(self, mock_torch):
        """Test the clear_gpu_memory utility function."""
        mock_torch.cuda.is_available.return_value = True

        clear_gpu_memory()

        mock_torch.cuda.empty_cache.assert_called_once()
        mock_torch.cuda.synchronize.assert_called_once()

    @patch("utils.gpu_memory_monitor.torch")
    def test_log_memory_stats(self, mock_torch):
        """Test memory stats logging."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.mem_get_info.return_value = (4 * 1024**3, 8 * 1024**3)

        monitor = GPUMemoryMonitor()
        # Should not raise any exceptions
        monitor.log_memory_stats("test_context")
