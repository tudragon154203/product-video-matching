import asyncio
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass
import cv2
import numpy as np
from common_py.logging_config import configure_logging
from config_loader import config

logger = configure_logging("video-crawler")


@dataclass
class VideoProperties:
    """Container for video metadata"""
    fps: float
    total_frames: int
    duration: float
    width: int
    height: int


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


class KeyframeExtractor:
    """Handles keyframe extraction from video files using OpenCV"""
    
    def __init__(self, config_override: Optional[KeyframeConfig] = None):
        """Initialize keyframe extractor
        
        Args:
            config_override: Optional configuration override for testing
        """
        self.keyframe_root_dir = Path(config.KEYFRAME_DIR)
        self.keyframe_root_dir.mkdir(parents=True, exist_ok=True)
        self.config = config_override or KeyframeConfig()
    
    async def extract_keyframes(self, video_url: str, video_id: str, local_path: Optional[str] = None) -> List[Tuple[float, str]]:
        """Extract keyframes from downloaded video file
        
        Args:
            video_url: URL of the video (for logging purposes)
            video_id: Unique video identifier for directory organization
            local_path: Path to the downloaded video file
            
        Returns:
            List of tuples containing (timestamp, frame_path)
            
        Raises:
            ValueError: If video file cannot be processed
        """
        if not self._validate_inputs(video_id, local_path):
            return []
        
        keyframe_dir = self._create_keyframe_directory(video_id)
        if not keyframe_dir:
            return []
        
        try:
            keyframes = await self._extract_frames_from_video(local_path, keyframe_dir, video_id)
            
            logger.info("Keyframe extraction completed", 
                       video_id=video_id, 
                       count=len(keyframes), 
                       local_path=local_path)
            
            return keyframes
            
        except Exception as e:
            logger.error("Failed to extract keyframes", 
                        video_id=video_id, 
                        local_path=local_path, 
                        error=str(e))
            return []
    
    def _validate_inputs(self, video_id: str, local_path: Optional[str]) -> bool:
        """Validate input parameters
        
        Args:
            video_id: Video identifier
            local_path: Path to video file
            
        Returns:
            True if inputs are valid, False otherwise
        """
        if not video_id or not video_id.strip():
            logger.error("Invalid video_id provided")
            return False
        
        if not local_path:
            logger.warning("No video file path provided", video_id=video_id)
            return False
        
        if not Path(local_path).exists():
            logger.warning("Video file does not exist", 
                         video_id=video_id, 
                         local_path=local_path)
            return False
        
        return True
    
    def _create_keyframe_directory(self, video_id: str) -> Optional[Path]:
        """Create directory for storing keyframes
        
        Args:
            video_id: Video identifier
            
        Returns:
            Path to keyframe directory or None if creation failed
        """
        try:
            keyframe_dir = self.keyframe_root_dir / video_id
            keyframe_dir.mkdir(parents=True, exist_ok=True)
            return keyframe_dir
        except Exception as e:
            logger.error("Failed to create keyframe directory", 
                        video_id=video_id, 
                        error=str(e))
            return None
    
    async def _extract_frames_from_video(self, video_path: str, keyframe_dir: Path, video_id: str) -> List[Tuple[float, str]]:
        """Extract frames from video file
        
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
            
            # Calculate extraction timestamps
            timestamps = self._calculate_extraction_timestamps(video_props)
            
            logger.info("Starting frame extraction", 
                       video_id=video_id, 
                       timestamps=timestamps,
                       video_duration=video_props.duration)
            
            # Extract frames
            keyframes = await self._extract_frames_at_timestamps(
                cap, timestamps, keyframe_dir, video_id, video_props
            )
            
            return keyframes
            
        finally:
            if cap is not None:
                cap.release()
    
    def _get_video_properties(self, cap: cv2.VideoCapture, video_id: str) -> VideoProperties:
        """Extract video properties from capture object
        
        Args:
            cap: OpenCV video capture object
            video_id: Video identifier for logging
            
        Returns:
            VideoProperties object with video metadata
        """
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps if fps > 0 else 0
        
        props = VideoProperties(
            fps=fps,
            total_frames=total_frames,
            duration=duration,
            width=width,
            height=height
        )
        
        logger.info("Video properties extracted", 
                   video_id=video_id, 
                   **props.__dict__)
        
        return props
    
    def _calculate_extraction_timestamps(self, video_props: VideoProperties) -> List[float]:
        """Calculate timestamps for frame extraction based on video duration
        
        Args:
            video_props: Video properties
            
        Returns:
            List of timestamps in seconds
        """
        duration = video_props.duration
        
        # For very short videos (≤2 seconds), use special handling
        if duration <= 2.0:
            # Use smaller buffer for very short videos
            buffer = min(self.config.FRAME_BUFFER_SECONDS, duration * 0.1)
            max_timestamp = duration - buffer
            
            if duration > 0.5:
                # Extract from middle for videos > 0.5s
                timestamps = [duration * 0.5]
            elif duration > 0.1:
                # Extract from near beginning for extremely short videos
                timestamps = [duration * 0.3]
            else:
                # For ultra-short videos, just extract from the first viable frame
                timestamps = [0.1]
            
            # Filter to ensure timestamps are valid
            valid_timestamps = [ts for ts in timestamps if ts < max_timestamp and ts >= 0]
            return valid_timestamps if valid_timestamps else [duration * 0.5]
        
        elif duration <= 30:
            # Short videos: extract at percentage points
            timestamps = [duration * ratio for ratio in self.config.SHORT_VIDEO_RATIO]
        elif duration <= 60:
            timestamps = self.config.MEDIUM_VIDEO_TIMESTAMPS.copy()
        elif duration <= 120:
            timestamps = self.config.LONG_VIDEO_TIMESTAMPS.copy()
        else:
            timestamps = self.config.VERY_LONG_VIDEO_TIMESTAMPS.copy()
        
        # Filter timestamps to be within video duration (with buffer)
        # Use smaller buffer for very short videos
        buffer = min(self.config.FRAME_BUFFER_SECONDS, duration * 0.1)
        max_timestamp = duration - buffer
        valid_timestamps = [ts for ts in timestamps if ts < max_timestamp and ts >= 0]
        
        # Ensure we have at least one timestamp if none are valid
        if not valid_timestamps and duration > 0.5:
            valid_timestamps = [duration * 0.5]
        
        return valid_timestamps
    
    async def _extract_frames_at_timestamps(
        self, 
        cap: cv2.VideoCapture, 
        timestamps: List[float], 
        keyframe_dir: Path, 
        video_id: str, 
        video_props: VideoProperties
    ) -> List[Tuple[float, str]]:
        """Extract frames at specified timestamps
        
        Args:
            cap: OpenCV video capture object
            timestamps: List of timestamps to extract frames at
            keyframe_dir: Directory to save frames
            video_id: Video identifier
            video_props: Video properties
            
        Returns:
            List of tuples containing (timestamp, frame_path)
        """
        keyframes = []
        
        for i, timestamp in enumerate(timestamps):
            try:
                frame_data = await self._extract_single_frame(
                    cap, timestamp, i, keyframe_dir, video_id, video_props
                )
                
                if frame_data:
                    keyframes.append(frame_data)
                    
            except Exception as e:
                logger.warning("Failed to extract frame", 
                             video_id=video_id, 
                             timestamp=timestamp, 
                             error=str(e))
                continue
        
        return keyframes
    
    async def _extract_single_frame(
        self, 
        cap: cv2.VideoCapture, 
        timestamp: float, 
        frame_index: int, 
        keyframe_dir: Path, 
        video_id: str, 
        video_props: VideoProperties
    ) -> Optional[Tuple[float, str]]:
        """Extract a single frame at the specified timestamp
        
        Args:
            cap: OpenCV video capture object
            timestamp: Timestamp to extract frame at
            frame_index: Index of the frame for naming
            keyframe_dir: Directory to save frame
            video_id: Video identifier
            video_props: Video properties
            
        Returns:
            Tuple of (timestamp, frame_path) or None if extraction failed
        """
        # Calculate frame number
        frame_number = int(timestamp * video_props.fps)
        
        # Seek to the frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        
        # Read the frame
        ret, frame = cap.read()
        if not ret:
            logger.warning("Could not read frame", 
                         video_id=video_id, 
                         timestamp=timestamp, 
                         frame_number=frame_number)
            return None
        
        # Validate frame quality
        blur_score = self._calculate_blur_score(frame)
        
        # Generate frame path
        frame_filename = f"frame_{frame_index}_{timestamp:.1f}s.{self.config.FRAME_FORMAT}"
        frame_path = keyframe_dir / frame_filename
        
        # Save the frame with specified quality
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.config.FRAME_QUALITY]
        success = cv2.imwrite(str(frame_path), frame, encode_params)
        
        if not success:
            logger.warning("Failed to save frame", 
                         video_id=video_id, 
                         timestamp=timestamp, 
                         frame_path=str(frame_path))
            return None
        
        logger.debug("Frame extracted successfully", 
                    video_id=video_id, 
                    timestamp=timestamp, 
                    blur_score=blur_score, 
                    frame_path=str(frame_path))
        
        return (timestamp, str(frame_path))
    
    def _calculate_blur_score(self, image: np.ndarray) -> float:
        """Calculate blur score using Laplacian variance
        
        Args:
            image: Input image array
            
        Returns:
            Blur score (higher values indicate sharper images)
        """
        try:
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Calculate Laplacian variance
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            variance = laplacian.var()
            
            return float(variance)
            
        except Exception as e:
            logger.error("Failed to calculate blur score", error=str(e))
            return 0.0
    
    def calculate_blur_score_from_file(self, image_path: str) -> float:
        """Calculate blur score from image file
        
        Args:
            image_path: Path to image file
            
        Returns:
            Blur score (higher values indicate sharper images)
        """
        try:
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if image is None:
                logger.warning("Could not load image", image_path=image_path)
                return 0.0
            
            return self._calculate_blur_score(image)
            
        except Exception as e:
            logger.error("Failed to calculate blur score from file", 
                        image_path=image_path, 
                        error=str(e))
            return 0.0