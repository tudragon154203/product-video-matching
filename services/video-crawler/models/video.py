"""
Video-related data models.

This module contains data structures for video processing and metadata.
"""

from dataclasses import dataclass


@dataclass
class VideoProperties:
    """Container for video metadata"""
    fps: float
    total_frames: int
    duration: float
    width: int
    height: int
