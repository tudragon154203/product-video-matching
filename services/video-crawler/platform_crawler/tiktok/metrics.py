"""
Simple metrics collection for TikTok download strategies.
Can be extended to integrate with proper monitoring systems.
"""
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional

from common_py.logging_config import configure_logging

logger = configure_logging("video-crawler:tiktok_metrics")


@dataclass
class DownloadMetrics:
    """Metrics for a single download operation."""
    strategy: str
    video_id: str
    url: str
    success: bool
    error_code: Optional[str] = None
    execution_time: Optional[float] = None
    file_size: Optional[int] = None
    api_execution_time: Optional[float] = None
    retries: int = 0
    timestamp: float = field(default_factory=time.time)


class TikTokMetricsCollector:
    """
    Simple in-memory metrics collector for TikTok downloads.

    This provides basic observability without external dependencies.
    Can be extended to integrate with Prometheus, DataDog, etc.
    """

    def __init__(self):
        # Counters by strategy and status
        self._counters = defaultdict(lambda: defaultdict(int))

        # Timings by strategy
        self._timings = defaultdict(list)

        # Recent download metrics (last 100)
        self._recent_downloads = []
        self._max_recent = 100

        # Error counts
        self._error_counts = defaultdict(int)

    def record_download_attempt(self, metrics: DownloadMetrics) -> None:
        """Record metrics for a download attempt."""
        # Update counters
        status_key = "success" if metrics.success else "failure"
        self._counters[metrics.strategy][status_key] += 1

        # Update error counts
        if not metrics.success and metrics.error_code:
            self._error_counts[metrics.error_code] += 1

        # Record timing
        if metrics.execution_time:
            self._timings[metrics.strategy].append(metrics.execution_time)

        # Keep recent downloads
        self._recent_downloads.append(metrics)
        if len(self._recent_downloads) > self._max_recent:
            self._recent_downloads.pop(0)

        # Log structured metrics
        logger.info(
            "TikTok download metrics recorded",
            strategy=metrics.strategy,
            video_id=metrics.video_id,
            success=metrics.success,
            execution_time=metrics.execution_time,
            api_execution_time=metrics.api_execution_time,
            file_size=metrics.file_size,
            error_code=metrics.error_code,
            retries=metrics.retries
        )

    def get_strategy_stats(self, strategy: str) -> Dict[str, any]:
        """Get statistics for a specific strategy."""
        counters = self._counters.get(strategy, {})
        timings = self._timings.get(strategy, [])

        total_attempts = sum(counters.values())
        success_rate = (counters.get("success", 0) / total_attempts * 100) if total_attempts > 0 else 0

        avg_execution_time = sum(timings) / len(timings) if timings else None

        return {
            "strategy": strategy,
            "total_attempts": total_attempts,
            "successful_downloads": counters.get("success", 0),
            "failed_downloads": counters.get("failure", 0),
            "success_rate": round(success_rate, 2),
            "avg_execution_time": round(avg_execution_time, 2) if avg_execution_time else None,
            "total_samples": len(timings)
        }

    def get_all_stats(self) -> Dict[str, any]:
        """Get statistics for all strategies."""
        all_stats = {}
        for strategy in self._counters.keys():
            all_stats[strategy] = self.get_strategy_stats(strategy)

        return {
            "strategies": all_stats,
            "total_error_counts": dict(self._error_counts),
            "recent_downloads_count": len(self._recent_downloads)
        }

    def get_recent_failures(self, limit: int = 10) -> list[Dict[str, any]]:
        """Get recent failed downloads."""
        failures = [d for d in self._recent_downloads if not d.success]
        return [
            {
                "video_id": d.video_id,
                "strategy": d.strategy,
                "error_code": d.error_code,
                "timestamp": d.timestamp
            }
            for d in failures[-limit:]
        ]

    def log_summary(self) -> None:
        """Log a summary of current metrics."""
        stats = self.get_all_stats()

        logger.info(
            "TikTok download metrics summary",
            total_strategies=len(stats["strategies"]),
            total_errors=sum(stats["total_error_counts"].values()),
            recent_downloads=stats["recent_downloads_count"]
        )

        for strategy_name, strategy_stats in stats["strategies"].items():
            logger.info(
                f"Strategy {strategy_name} metrics",
                attempts=strategy_stats["total_attempts"],
                success_rate=f"{strategy_stats['success_rate']}%",
                avg_time=strategy_stats["avg_execution_time"]
            )


# Global metrics collector instance
_metrics_collector = TikTokMetricsCollector()


def get_metrics_collector() -> TikTokMetricsCollector:
    """Get the global metrics collector instance."""
    return _metrics_collector


def record_download_metrics(
    strategy: str,
    video_id: str,
    url: str,
    success: bool,
    error_code: Optional[str] = None,
    execution_time: Optional[float] = None,
    file_size: Optional[int] = None,
    api_execution_time: Optional[float] = None,
    retries: int = 0
) -> None:
    """
    Record download metrics using the global collector.

    This is a convenience function for recording metrics.
    """
    metrics = DownloadMetrics(
        strategy=strategy,
        video_id=video_id,
        url=url,
        success=success,
        error_code=error_code,
        execution_time=execution_time,
        file_size=file_size,
        api_execution_time=api_execution_time,
        retries=retries
    )

    _metrics_collector.record_download_attempt(metrics)
