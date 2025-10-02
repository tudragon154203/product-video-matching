"""
Video-related data models.

This module contains data structures for video processing and metadata.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class VideoProperties:
    """Container for video metadata"""
    fps: float
    total_frames: int
    duration: float
    width: int
    height: int


@dataclass
class Keyframe:
    """Container for keyframe metadata"""
    timestamp: float
    frame_path: str


@dataclass
class Video:
    """Container for video metadata including TikTok-specific fields"""
    video_id: str
    platform: str
    url: str
    title: Optional[str] = None
    duration_s: Optional[int] = None
    published_at: Optional[str] = None
    job_id: Optional[str] = None
    created_at: Optional[str] = None

    # TikTok-specific fields
    download_url: Optional[str] = None
    local_path: Optional[str] = None
    has_download: bool = False
    keyframes: List[Keyframe] = None

    def __post_init__(self):
        if self.keyframes is None:
            self.keyframes = []
