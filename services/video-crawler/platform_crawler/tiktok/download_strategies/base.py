from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class TikTokAntiBotError(Exception):
    """Custom exception for TikTok anti-bot detection"""
    pass


class TikTokDownloadStrategy(ABC):
    """Abstract base class for TikTok download strategies."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.retries = config.get("retries", 3)
        self.timeout = config.get("timeout", 30)

    @abstractmethod
    def download_video(self, url: str, video_id: str, output_path: str) -> Optional[str]:
        """
        Download a TikTok video using the specific strategy.

        Args:
            url: TikTok video URL
            video_id: Unique video identifier
            output_path: Directory to save the video

        Returns:
            Local path to downloaded video or None if failed
        """
        pass

    @abstractmethod
    async def extract_keyframes(
        self, video_path: str, video_id: str
    ) -> Tuple[Optional[str], List[Tuple[float, str]]]:
        """
        Extract keyframes from a downloaded TikTok video.

        Args:
            video_path: Path to the downloaded video
            video_id: Unique video identifier

        Returns:
            Tuple of (keyframes_dir, list_of_timestamps_and_paths)
        """
        pass
