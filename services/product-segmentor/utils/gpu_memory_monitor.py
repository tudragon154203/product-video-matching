"""GPU memory monitoring utilities for adaptive concurrency control."""

import torch
from typing import Tuple
from common_py.logging_config import configure_logging

logger = configure_logging("product-segmentor:gpu_memory_monitor")


class GPUMemoryMonitor:
    """Monitor GPU memory usage and provide adaptive concurrency control."""

    def __init__(self, memory_threshold: float = 0.85):
        """Initialize GPU memory monitor.

        Args:
            memory_threshold: Fraction of GPU memory (0.0-1.0) at which to block new tasks
        """
        self.memory_threshold = memory_threshold
        self.cuda_available = torch.cuda.is_available()
        self._cleanup_counter = 0
        self._cleanup_interval = 10  # Run cleanup every N frames

        if self.cuda_available:
            logger.info(
                "GPU memory monitor initialized",
                threshold=memory_threshold,
                device_count=torch.cuda.device_count(),
            )
        else:
            logger.info("GPU not available, memory monitoring disabled")

    def get_memory_info(self) -> Tuple[int, int, float]:
        """Get current GPU memory usage.

        Returns:
            Tuple of (used_bytes, total_bytes, usage_fraction)
        """
        if not self.cuda_available:
            return (0, 0, 0.0)

        try:
            # Get memory info for default device
            free_bytes, total_bytes = torch.cuda.mem_get_info()
            used_bytes = total_bytes - free_bytes
            usage_fraction = used_bytes / total_bytes if total_bytes > 0 else 0.0

            return (used_bytes, total_bytes, usage_fraction)
        except Exception as e:
            logger.warning("Failed to get GPU memory info", error=str(e))
            return (0, 0, 0.0)

    def should_block_new_task(self) -> bool:
        """Check if new tasks should be blocked due to memory pressure.

        Returns:
            True if memory usage exceeds threshold
        """
        if not self.cuda_available:
            return False

        used_bytes, total_bytes, usage_fraction = self.get_memory_info()

        if usage_fraction >= self.memory_threshold:
            logger.warning(
                "GPU memory threshold exceeded, blocking new tasks",
                used_mb=used_bytes / (1024 * 1024),
                total_mb=total_bytes / (1024 * 1024),
                usage_percent=usage_fraction * 100,
                threshold_percent=self.memory_threshold * 100,
            )
            return True

        return False

    def periodic_cleanup(self, force: bool = False) -> None:
        """Perform periodic GPU memory cleanup.

        Args:
            force: Force cleanup regardless of counter
        """
        if not self.cuda_available:
            return

        self._cleanup_counter += 1

        if force or self._cleanup_counter >= self._cleanup_interval:
            try:
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                self._cleanup_counter = 0

                used_bytes, total_bytes, usage_fraction = self.get_memory_info()
                logger.debug(
                    "GPU memory cleanup performed",
                    used_mb=used_bytes / (1024 * 1024),
                    total_mb=total_bytes / (1024 * 1024),
                    usage_percent=usage_fraction * 100,
                )
            except Exception as e:
                logger.warning("GPU cleanup failed", error=str(e))

    def log_memory_stats(self, context: str = "") -> None:
        """Log current GPU memory statistics.

        Args:
            context: Context string for logging
        """
        if not self.cuda_available:
            return

        used_bytes, total_bytes, usage_fraction = self.get_memory_info()

        logger.info(
            "GPU memory stats",
            context=context,
            used_mb=round(used_bytes / (1024 * 1024), 2),
            total_mb=round(total_bytes / (1024 * 1024), 2),
            free_mb=round((total_bytes - used_bytes) / (1024 * 1024), 2),
            usage_percent=round(usage_fraction * 100, 2),
        )


def clear_gpu_memory() -> None:
    """Force clear GPU memory cache."""
    if torch.cuda.is_available():
        try:
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            logger.debug("GPU memory cache cleared")
        except Exception as e:
            logger.warning("Failed to clear GPU memory", error=str(e))
