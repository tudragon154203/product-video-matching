"""
Length-adaptive keyframe extractor implementation.

This module provides a concrete implementation of keyframe extraction that adapts
the number and timing of extracted frames based on video duration.
"""

import asyncio
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass
import cv2
import numpy as np
from common_py.logging_config import configure_logging
from .abstract_extractor import AbstractKeyframeExtractor

logger = configure_logging("video-crawler")


@dataclass
class KeyframeConfig:
    """Configuration for keyframe extraction"""
    # Default timestamps for different video durations
    SHORT_VIDEO_RATIO = [0.2, 0.5, 0.8]  # For videos <= 30s
    MEDIUM_VIDEO_TIMESTAMPS = [10.0, 30.0, 50.0]  # For videos <= 60s
    LONG_VIDEO_TIMESTAMPS = [10.0, 30.0, 60.0, 90.0]  # For videos <= 120s
    VERY_LONG_VIDEO_TIMESTAMPS = [10.0, 30.0, 60.0, 90.0, 120.0]  # For videos > 120s
    
    # Quality settings
    MIN_BLUR_THRESHOLD = 100.0  # Minimum acceptable blur score
    FRAME_BUFFER_SECONDS = 1.0  # Buffer from end of video
    
    # File settings
    FRAME_QUALITY = 95  # JPEG quality (0-100)
    FRAME_FORMAT = "jpg"


class LengthAdaptiveKeyframeExtractor(AbstractKeyframeExtractor):
    """
    Keyframe extractor that adapts extraction strategy based on video length.
    
    This implementation uses different timestamp selection strategies based on video duration:
    - Short videos (≤30s): Use proportional timestamps (20%, 50%, 80%)
    - Medium videos (≤60s): Use fixed timestamps [10s, 30s, 50s]
    - Long videos (≤120s): Use fixed timestamps [10s, 30s, 60s, 90s]
    - Very long videos (>120s): Use fixed timestamps [10s, 30s, 60s, 90s, 120s]
    """
    
    def __init__(self, keyframe_root_dir: Optional[str] = None, config_override: Optional[KeyframeConfig] = None):
        """
        Initialize the length-adaptive keyframe extractor.
        
        Args:
            keyframe_root_dir: Custom root directory for keyframes (optional)
            config_override: Optional configuration override for testing
        """
        super().__init__(keyframe_root_dir)
        self.config = config_override or KeyframeConfig()
    
    async def _extract_frames_from_video(
        self, 
        video_path: str, 
        keyframe_dir: Path, 
        video_id: str
    ) -> List[Tuple[float, str]]:
        """
        Extract frames from video file using length-adaptive strategy.
        
        Args:
            video_path: Path to the video file
            keyframe_dir: Directory to save extracted frames
            video_id: Video identifier for logging
            
        Returns:
            List of tuples containing (timestamp, frame_path)
            
        Raises:
            ValueError: If video cannot be opened or processed
        """
        cap = None
        try:
            # Open and validate video
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Could not open video file: {video_path}")
            
            # Get video properties
            video_props = self._get_video_properties(cap, video_id)
            if video_props.duration <= 0:
                raise ValueError(f"Invalid video duration: {video_props.duration}")
            
            # Calculate extraction timestamps based on video length
            timestamps = self._calculate_extraction_timestamps(video_props)
            
            logger.info("Starting frame extraction", 
                       video_id=video_id, 
                       timestamps=timestamps,
                       video_duration=video_props.duration)
            
            # Extract frames at calculated timestamps
            keyframes = await self._extract_frames_at_timestamps(
                cap, timestamps, keyframe_dir, video_id, video_props
            )
            
            return keyframes
            
        finally:
            if cap is not None:
                cap.release()
    
    def _calculate_extraction_timestamps(self, video_props) -> List[float]:
        """
        Calculate timestamps for frame extraction based on video duration.
        
        Args:
            video_props: VideoProperties object containing video metadata
            
        Returns:
            List of timestamps in seconds where frames should be extracted
        """
        duration = video_props.duration
        
        # Handle very short videos separately (≤2 seconds)
        if duration <= 2.0:
            # For very short videos, just extract from the middle
            return [duration / 2.0]
        
        # Short videos (≤30 seconds): Use proportional timestamps
        if duration <= 30.0:
            timestamps = [duration * ratio for ratio in self.config.SHORT_VIDEO_RATIO]
        # Medium videos (≤60 seconds): Use fixed timestamps
        elif duration <= 60.0:
            timestamps = self.config.MEDIUM_VIDEO_TIMESTAMPS[:]
        # Long videos (≤120 seconds): Use fixed timestamps
        elif duration <= 120.0:
            timestamps = self.config.LONG_VIDEO_TIMESTAMPS[:]
        # Very long videos (>120 seconds): Use fixed timestamps
        else:
            timestamps = self.config.VERY_LONG_VIDEO_TIMESTAMPS[:]
        
        # Filter out timestamps that are too close to the end of the video
        buffer = self.config.FRAME_BUFFER_SECONDS
        valid_timestamps = [ts for ts in timestamps if ts < (duration - buffer)]
        
        # Ensure we have at least one valid timestamp
        if not valid_timestamps and timestamps:
            # If all timestamps were filtered out, use the middle of the video
            valid_timestamps = [duration / 2.0]
        
        logger.debug("Calculated extraction timestamps", 
                    video_duration=duration,
                    original_timestamps=timestamps,
                    valid_timestamps=valid_timestamps,
                    filtered_count=len(timestamps) - len(valid_timestamps))
        
        return valid_timestamps
    
    async def _extract_frames_at_timestamps(
        self, 
        cap: cv2.VideoCapture, 
        timestamps: List[float], 
        keyframe_dir: Path, 
        video_id: str,
        video_props
    ) -> List[Tuple[float, str]]:
        """
        Extract frames at specified timestamps.
        
        Args:
            cap: OpenCV VideoCapture object
            timestamps: List of timestamps to extract frames from
            keyframe_dir: Directory to save frames
            video_id: Video identifier for logging
            video_props: Video properties object
            
        Returns:
            List of tuples containing (timestamp, frame_path)
        """
        extracted_frames = []
        
        for timestamp in timestamps:
            try:
                # Seek to the target timestamp
                if not self._seek_to_timestamp(cap, timestamp, video_props.fps):
                    logger.warning("Failed to seek to timestamp", 
                                 video_id=video_id, 
                                 timestamp=timestamp)
                    continue
                
                # Read the frame
                ret, frame = cap.read()
                if not ret or frame is None:
                    logger.warning("Failed to read frame at timestamp", 
                                 video_id=video_id, 
                                 timestamp=timestamp)
                    continue
                
                # Check frame quality (blur detection)
                blur_score = self._calculate_blur_score(frame)
                if blur_score < self.config.MIN_BLUR_THRESHOLD:
                    logger.debug("Frame rejected due to blur", 
                               video_id=video_id, 
                               timestamp=timestamp,
                               blur_score=blur_score,
                               threshold=self.config.MIN_BLUR_THRESHOLD)
                    # For now, we still save blurry frames but log the issue
                    # In the future, we could implement frame replacement logic
                
                # Generate frame filename and path
                frame_filename = self._generate_frame_filename(video_id, timestamp, self.config.FRAME_FORMAT)
                frame_path = keyframe_dir / frame_filename
                
                # Save the frame
                if self._save_frame(frame, str(frame_path), self.config.FRAME_QUALITY):
                    extracted_frames.append((timestamp, str(frame_path)))
                    logger.debug("Frame extracted successfully", 
                               video_id=video_id,
                               timestamp=timestamp,
                               frame_path=str(frame_path),
                               blur_score=blur_score)
                else:
                    logger.error("Failed to save frame", 
                               video_id=video_id, 
                               timestamp=timestamp,
                               frame_path=str(frame_path))
                
            except Exception as e:
                logger.error("Error extracting frame at timestamp", 
                           video_id=video_id, 
                           timestamp=timestamp, 
                           error=str(e))
                continue
        
        logger.info("Frame extraction completed", 
                   video_id=video_id, 
                   total_extracted=len(extracted_frames),
                   total_requested=len(timestamps))
        
        return extracted_frames