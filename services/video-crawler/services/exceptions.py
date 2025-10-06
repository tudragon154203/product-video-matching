"""Custom exceptions for the video crawler service."""


class VideoCrawlerError(Exception):
    """Base exception for video crawler service."""

    def __init__(self, message: str, video_id: Optional[str] = None, job_id: Optional[str] = None):
        self.video_id = video_id
        self.job_id = job_id
        super().__init__(message)


class VideoProcessingError(VideoCrawlerError):
    """Raised when video processing fails."""

    def __init__(self, message: str, video_id: Optional[str] = None, platform: Optional[str] = None):
        self.platform = platform
        super().__init__(message, video_id)


class KeyframeExtractionError(VideoProcessingError):
    """Raised when keyframe extraction fails."""

    def __init__(self, message: str, video_id: Optional[str] = None, frame_count: int = 0):
        self.frame_count = frame_count
        super().__init__(message, video_id)


class PlatformCrawlerError(VideoCrawlerError):
    """Raised when platform crawler encounters an error."""

    def __init__(self, message: str, platform: str, query: Optional[str] = None):
        self.platform = platform
        self.query = query
        super().__init__(message)


class VideoDownloadError(VideoProcessingError):
    """Raised when video download fails."""

    def __init__(self, message: str, video_id: Optional[str] = None, url: Optional[str] = None):
        self.url = url
        super().__init__(message, video_id)


class DatabaseOperationError(VideoCrawlerError):
    """Raised when database operations fail."""

    def __init__(self, message: str, operation: str, table: Optional[str] = None):
        self.operation = operation
        self.table = table
        super().__init__(message)


class CleanupOperationError(VideoCrawlerError):
    """Raised when cleanup operations fail."""

    def __init__(self, message: str, directory: Optional[str] = None, files_affected: int = 0):
        self.directory = directory
        self.files_affected = files_affected
        super().__init__(message)


class ConfigurationError(VideoCrawlerError):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str, config_key: Optional[str] = None):
        self.config_key = config_key
        super().__init__(message)