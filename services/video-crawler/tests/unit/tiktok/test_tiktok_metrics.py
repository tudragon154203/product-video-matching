# Unused import removed: pytest
import time
from unittest.mock import patch

from platform_crawler.tiktok.metrics import (
    DownloadMetrics,
    TikTokMetricsCollector,
    get_metrics_collector,
    record_download_metrics
)


class TestDownloadMetrics:
    """Test the DownloadMetrics dataclass."""

    def test_download_metrics_creation(self):
        """Test creating DownloadMetrics instance."""
        metrics = DownloadMetrics(
            strategy="scrapling-api",
            video_id="test123",
            url="https://tiktok.com/test",
            success=True,
            execution_time=10.5,
            file_size=1000000,
            api_execution_time=5.0,
            retries=1
        )

        assert metrics.strategy == "scrapling-api"
        assert metrics.video_id == "test123"
        assert metrics.url == "https://tiktok.com/test"
        assert metrics.success is True
        assert metrics.execution_time == 10.5
        assert metrics.file_size == 1000000
        assert metrics.api_execution_time == 5.0
        assert metrics.retries == 1
        assert isinstance(metrics.timestamp, float)

    def test_download_metrics_defaults(self):
        """Test DownloadMetrics with default values."""
        before = time.time()
        metrics = DownloadMetrics(
            strategy="yt-dlp",
            video_id="test456",
            url="https://tiktok.com/test2",
            success=False
        )
        after = time.time()

        assert metrics.strategy == "yt-dlp"
        assert metrics.video_id == "test456"
        assert metrics.url == "https://tiktok.com/test2"
        assert metrics.success is False
        assert metrics.error_code is None
        assert metrics.execution_time is None
        assert metrics.file_size is None
        assert metrics.api_execution_time is None
        assert metrics.retries == 0
        assert before <= metrics.timestamp <= after


class TestTikTokMetricsCollector:
    """Test the TikTokMetricsCollector functionality."""

    def test_collector_initialization(self):
        """Test metrics collector initialization."""
        collector = TikTokMetricsCollector()
        assert len(collector._counters) == 0
        assert len(collector._timings) == 0
        assert len(collector._recent_downloads) == 0
        assert len(collector._error_counts) == 0
        assert collector._max_recent == 100

    def test_record_download_success(self):
        """Test recording a successful download."""
        collector = TikTokMetricsCollector()
        metrics = DownloadMetrics(
            strategy="scrapling-api",
            video_id="test123",
            url="https://tiktok.com/test",
            success=True,
            execution_time=10.5,
            file_size=1000000
        )

        collector.record_download_attempt(metrics)

        # Check counters
        assert collector._counters["scrapling-api"]["success"] == 1
        assert collector._counters["scrapling-api"]["failure"] == 0

        # Check timings
        assert len(collector._timings["scrapling-api"]) == 1
        assert collector._timings["scrapling-api"][0] == 10.5

        # Check recent downloads
        assert len(collector._recent_downloads) == 1
        assert collector._recent_downloads[0].strategy == "scrapling-api"
        assert collector._recent_downloads[0].success is True

    def test_record_download_failure(self):
        """Test recording a failed download."""
        collector = TikTokMetricsCollector()
        metrics = DownloadMetrics(
            strategy="yt-dlp",
            video_id="test456",
            url="https://tiktok.com/test2",
            success=False,
            error_code="NAVIGATION_FAILED",
            execution_time=5.0
        )

        collector.record_download_attempt(metrics)

        # Check counters
        assert collector._counters["yt-dlp"]["success"] == 0
        assert collector._counters["yt-dlp"]["failure"] == 1

        # Check error counts
        assert collector._error_counts["NAVIGATION_FAILED"] == 1

        # Check timings
        assert len(collector._timings["yt-dlp"]) == 1
        assert collector._timings["yt-dlp"][0] == 5.0

    def test_multiple_downloads_same_strategy(self):
        """Test recording multiple downloads for the same strategy."""
        collector = TikTokMetricsCollector()

        # Record multiple downloads
        for i in range(5):
            metrics = DownloadMetrics(
                strategy="scrapling-api",
                video_id=f"test{i}",
                url=f"https://tiktok.com/test{i}",
                success=i < 4,  # First 4 succeed, last 1 fails
                execution_time=float(i + 1)
            )
            collector.record_download_attempt(metrics)

        # Check counters
        assert collector._counters["scrapling-api"]["success"] == 4
        assert collector._counters["scrapling-api"]["failure"] == 1

        # Check timings
        assert len(collector._timings["scrapling-api"]) == 5
        assert collector._timings["scrapling-api"] == [1.0, 2.0, 3.0, 4.0, 5.0]

        # Check recent downloads
        assert len(collector._recent_downloads) == 5

    def test_recent_downloads_limit(self):
        """Test that recent downloads are limited to max_recent."""
        collector = TikTokMetricsCollector()
        collector._max_recent = 3  # Small limit for testing

        # Record more downloads than the limit
        for i in range(5):
            metrics = DownloadMetrics(
                strategy="scrapling-api",
                video_id=f"test{i}",
                url=f"https://tiktok.com/test{i}",
                success=True
            )
            collector.record_download_attempt(metrics)

        # Should only keep the most recent 3
        assert len(collector._recent_downloads) == 3
        assert collector._recent_downloads[0].video_id == "test2"
        assert collector._recent_downloads[2].video_id == "test4"

    def test_get_strategy_stats(self):
        """Test getting statistics for a specific strategy."""
        collector = TikTokMetricsCollector()

        # Record some mixed results
        downloads = [
            DownloadMetrics("scrapling-api", "test1", "url1", True, execution_time=5.0),
            DownloadMetrics("scrapling-api", "test2", "url2", True, execution_time=7.0),
            DownloadMetrics("scrapling-api", "test3", "url3", False, execution_time=3.0),
            DownloadMetrics("scrapling-api", "test4", "url4", True, execution_time=9.0),
        ]

        for metrics in downloads:
            collector.record_download_attempt(metrics)

        stats = collector.get_strategy_stats("scrapling-api")

        assert stats["strategy"] == "scrapling-api"
        assert stats["total_attempts"] == 4
        assert stats["successful_downloads"] == 3
        assert stats["failed_downloads"] == 1
        assert stats["success_rate"] == 75.0
        assert stats["avg_execution_time"] == 6.0
        assert stats["total_samples"] == 4

    def test_get_strategy_stats_empty(self):
        """Test getting statistics for strategy with no downloads."""
        collector = TikTokMetricsCollector()
        stats = collector.get_strategy_stats("nonexistent")

        assert stats["strategy"] == "nonexistent"
        assert stats["total_attempts"] == 0
        assert stats["successful_downloads"] == 0
        assert stats["failed_downloads"] == 0
        assert stats["success_rate"] == 0
        assert stats["avg_execution_time"] is None
        assert stats["total_samples"] == 0

    def test_get_all_stats(self):
        """Test getting all statistics."""
        collector = TikTokMetricsCollector()

        # Record downloads for different strategies
        downloads = [
            DownloadMetrics("scrapling-api", "test1", "url1", True, execution_time=5.0),
            DownloadMetrics("scrapling-api", "test2", "url2", False, error_code="ERROR1"),
            DownloadMetrics("yt-dlp", "test3", "url3", True, execution_time=8.0),
            DownloadMetrics("yt-dlp", "test4", "url4", False, error_code="ERROR2"),
        ]

        for metrics in downloads:
            collector.record_download_attempt(metrics)

        all_stats = collector.get_all_stats()

        assert "strategies" in all_stats
        assert "total_error_counts" in all_stats
        assert "recent_downloads_count" in all_stats

        # Check strategy stats
        assert "scrapling-api" in all_stats["strategies"]
        assert "yt-dlp" in all_stats["strategies"]

        # Check error counts
        assert all_stats["total_error_counts"]["ERROR1"] == 1
        assert all_stats["total_error_counts"]["ERROR2"] == 1

        # Check recent downloads count
        assert all_stats["recent_downloads_count"] == 4

    def test_get_recent_failures(self):
        """Test getting recent failures."""
        collector = TikTokMetricsCollector()

        # Record mixed results
        downloads = [
            DownloadMetrics("scrapling-api", "test1", "url1", True),
            DownloadMetrics("scrapling-api", "test2", "url2", False, error_code="ERROR1"),
            DownloadMetrics("yt-dlp", "test3", "url3", False, error_code="ERROR2"),
            DownloadMetrics("scrapling-api", "test4", "url4", True),
            DownloadMetrics("yt-dlp", "test5", "url5", False, error_code="ERROR3"),
        ]

        for metrics in downloads:
            collector.record_download_attempt(metrics)

        failures = collector.get_recent_failures(limit=10)

        assert len(failures) == 3
        assert failures[0]["video_id"] == "test2"
        assert failures[0]["strategy"] == "scrapling-api"
        assert failures[0]["error_code"] == "ERROR1"
        assert failures[1]["video_id"] == "test3"
        assert failures[1]["strategy"] == "yt-dlp"
        assert failures[1]["error_code"] == "ERROR2"

    @patch('platform_crawler.tiktok.metrics.logger')
    def test_log_summary(self, mock_logger):
        """Test logging summary."""
        collector = TikTokMetricsCollector()

        # Record some downloads
        downloads = [
            DownloadMetrics("scrapling-api", "test1", "url1", True),
            DownloadMetrics("scrapling-api", "test2", "url2", False, error_code="ERROR1"),
        ]

        for metrics in downloads:
            collector.record_download_attempt(metrics)

        collector.log_summary()

        # Should have called logger.info multiple times
        assert mock_logger.info.call_count >= 3  # Summary + strategy stats


class TestGlobalMetricsFunctions:
    """Test global metrics functions."""

    def test_get_metrics_collector(self):
        """Test getting the global metrics collector."""
        collector = get_metrics_collector()
        assert isinstance(collector, TikTokMetricsCollector)

        # Should return the same instance
        collector2 = get_metrics_collector()
        assert collector is collector2

    @patch('platform_crawler.tiktok.metrics._metrics_collector')
    def test_record_download_metrics(self, mock_collector):
        """Test the convenience function for recording metrics."""
        record_download_metrics(
            strategy="scrapling-api",
            video_id="test123",
            url="https://tiktok.com/test",
            success=True,
            execution_time=10.5,
            file_size=1000000
        )

        mock_collector.record_download_attempt.assert_called_once()

        # Check the arguments passed to record_download_attempt
        call_args = mock_collector.record_download_attempt.call_args[0][0]
        assert isinstance(call_args, DownloadMetrics)
        assert call_args.strategy == "scrapling-api"
        assert call_args.video_id == "test123"
        assert call_args.url == "https://tiktok.com/test"
        assert call_args.success is True
        assert call_args.execution_time == 10.5
        assert call_args.file_size == 1000000
