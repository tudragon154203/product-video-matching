"""Unit tests for custom exceptions."""

import pytest

from services.exceptions import (
    VideoCrawlerError,
    VideoProcessingError,
    KeyframeExtractionError,
    PlatformCrawlerError,
    VideoDownloadError,
    DatabaseOperationError,
    CleanupOperationError,
    ConfigurationError
)

pytestmark = pytest.mark.unit


class TestVideoCrawlerError:
    """Tests for VideoCrawlerError base exception."""

    def test_video_crawler_error_basic(self):
        """Test VideoCrawlerError with basic message."""
        error = VideoCrawlerError("Test error")

        assert str(error) == "Test error"
        assert error.video_id is None
        assert error.job_id is None

    def test_video_crawler_error_with_video_id(self):
        """Test VideoCrawlerError with video ID."""
        error = VideoCrawlerError("Test error", video_id="video_123")

        assert str(error) == "Test error"
        assert error.video_id == "video_123"
        assert error.job_id is None

    def test_video_crawler_error_with_job_id(self):
        """Test VideoCrawlerError with job ID."""
        error = VideoCrawlerError("Test error", job_id="job_456")

        assert str(error) == "Test error"
        assert error.video_id is None
        assert error.job_id == "job_456"

    def test_video_crawler_error_with_both_ids(self):
        """Test VideoCrawlerError with both video and job IDs."""
        error = VideoCrawlerError("Test error", video_id="video_123", job_id="job_456")

        assert str(error) == "Test error"
        assert error.video_id == "video_123"
        assert error.job_id == "job_456"


class TestVideoProcessingError:
    """Tests for VideoProcessingError."""

    def test_video_processing_error_basic(self):
        """Test VideoProcessingError with basic message."""
        error = VideoProcessingError("Processing failed")

        assert str(error) == "Processing failed"
        assert error.platform is None

    def test_video_processing_error_with_platform(self):
        """Test VideoProcessingError with platform."""
        error = VideoProcessingError("Processing failed", platform="youtube", video_id="video_123")

        assert str(error) == "Processing failed"
        assert error.platform == "youtube"
        assert error.video_id == "video_123"


class TestKeyframeExtractionError:
    """Tests for KeyframeExtractionError."""

    def test_keyframe_extraction_error_basic(self):
        """Test KeyframeExtractionError with basic message."""
        error = KeyframeExtractionError("Extraction failed")

        assert str(error) == "Extraction failed"
        assert error.frame_count == 0

    def test_keyframe_extraction_error_with_frame_count(self):
        """Test KeyframeExtractionError with frame count."""
        error = KeyframeExtractionError("Extraction failed", video_id="video_123", frame_count=5)

        assert str(error) == "Extraction failed"
        assert error.video_id == "video_123"
        assert error.frame_count == 5


class TestPlatformCrawlerError:
    """Tests for PlatformCrawlerError."""

    def test_platform_crawler_error_basic(self):
        """Test PlatformCrawlerError with basic message."""
        error = PlatformCrawlerError("Crawler failed", "youtube")

        assert str(error) == "Crawler failed"
        assert error.platform == "youtube"
        assert error.query is None

    def test_platform_crawler_error_with_query(self):
        """Test PlatformCrawlerError with query."""
        error = PlatformCrawlerError("Crawler failed", "youtube", "test query")

        assert str(error) == "Crawler failed"
        assert error.platform == "youtube"
        assert error.query == "test query"


class TestVideoDownloadError:
    """Tests for VideoDownloadError."""

    def test_video_download_error_basic(self):
        """Test VideoDownloadError with basic message."""
        error = VideoDownloadError("Download failed", video_id="video_123")

        assert str(error) == "Download failed"
        assert error.video_id == "video_123"
        assert error.url is None

    def test_video_download_error_with_url(self):
        """Test VideoDownloadError with URL."""
        error = VideoDownloadError("Download failed", video_id="video_123", url="https://test.com")

        assert str(error) == "Download failed"
        assert error.video_id == "video_123"
        assert error.url == "https://test.com"


class TestDatabaseOperationError:
    """Tests for DatabaseOperationError."""

    def test_database_operation_error_basic(self):
        """Test DatabaseOperationError with basic message."""
        error = DatabaseOperationError("DB failed", "insert")

        assert str(error) == "DB failed"
        assert error.operation == "insert"
        assert error.table is None

    def test_database_operation_error_with_table(self):
        """Test DatabaseOperationError with table."""
        error = DatabaseOperationError("DB failed", "insert", "videos")

        assert str(error) == "DB failed"
        assert error.operation == "insert"
        assert error.table == "videos"


class TestCleanupOperationError:
    """Tests for CleanupOperationError."""

    def test_cleanup_operation_error_basic(self):
        """Test CleanupOperationError with basic message."""
        error = CleanupOperationError("Cleanup failed")

        assert str(error) == "Cleanup failed"
        assert error.directory is None
        assert error.files_affected == 0

    def test_cleanup_operation_error_with_directory(self):
        """Test CleanupOperationError with directory."""
        error = CleanupOperationError("Cleanup failed", "/test/dir", 10)

        assert str(error) == "Cleanup failed"
        assert error.directory == "/test/dir"
        assert error.files_affected == 10


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_configuration_error_basic(self):
        """Test ConfigurationError with basic message."""
        error = ConfigurationError("Config failed")

        assert str(error) == "Config failed"
        assert error.config_key is None

    def test_configuration_error_with_key(self):
        """Test ConfigurationError with config key."""
        error = ConfigurationError("Config failed", "VIDEO_DIR")

        assert str(error) == "Config failed"
        assert error.config_key == "VIDEO_DIR"


class TestExceptionInheritance:
    """Tests for exception inheritance hierarchy."""

    def test_video_processing_error_inheritance(self):
        """Test that VideoProcessingError inherits from VideoCrawlerError."""
        error = VideoProcessingError("Test")
        assert isinstance(error, VideoCrawlerError)

    def test_keyframe_extraction_error_inheritance(self):
        """Test that KeyframeExtractionError inherits from VideoProcessingError."""
        error = KeyframeExtractionError("Test")
        assert isinstance(error, VideoProcessingError)
        assert isinstance(error, VideoCrawlerError)

    def test_video_download_error_inheritance(self):
        """Test that VideoDownloadError inherits from VideoProcessingError."""
        error = VideoDownloadError("Test")
        assert isinstance(error, VideoProcessingError)
        assert isinstance(error, VideoCrawlerError)

    def test_other_errors_inheritance(self):
        """Test that other errors inherit from VideoCrawlerError."""
        assert issubclass(PlatformCrawlerError, VideoCrawlerError)
        assert issubclass(DatabaseOperationError, VideoCrawlerError)
        assert issubclass(CleanupOperationError, VideoCrawlerError)
        assert issubclass(ConfigurationError, VideoCrawlerError)
