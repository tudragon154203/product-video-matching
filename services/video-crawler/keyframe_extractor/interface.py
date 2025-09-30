"""
Interface for keyframe extraction from video files.

This module defines the contract that all keyframe extractors must implement,
ensuring consistency and interchangeability between different extraction strategies.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Optional


class KeyframeExtractorInterface(ABC):
    """
    Interface for keyframe extraction from video files.

    This interface defines the contract that all keyframe extractors must implement,
    ensuring consistency across different extraction strategies and algorithms.
    """

    @abstractmethod
    async def extract_keyframes(
        self,
        video_url: str,
        video_id: str,
        local_path: Optional[str] = None
    ) -> List[Tuple[float, str]]:
        """
        Extract keyframes from a video file.

        Args:
            video_url: URL of the video (for logging and metadata)
            video_id: Unique identifier for the video
            local_path: Path to the downloaded video file

        Returns:
            List of tuples containing (timestamp, frame_path)

        Raises:
            ValueError: If input parameters are invalid
            FileNotFoundError: If video file cannot be found
            RuntimeError: If extraction process fails
        """
        pass
