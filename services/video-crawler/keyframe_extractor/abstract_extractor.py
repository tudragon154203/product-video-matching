"""
Abstract base class for keyframe extractors.

This module provides a common implementation foundation for all keyframe extractors,
including shared utilities, logging, and common validation logic.
"""

from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

from common_py.logging_config import configure_logging
from config_loader import config
from .interface import KeyframeExtractorInterface

logger = configure_logging("video-crawler:abstract_extractor")


if TYPE_CHECKING:
    from models.video import VideoProperties


class AbstractKeyframeExtractor(KeyframeExtractorInterface, ABC):
    """
    Abstract base class providing common functionality for keyframe extractors.

    This class implements common operations like directory management, input validation,
    blur score calculation, and provides template methods for the extraction workflow.
    """

    def __init__(self, keyframe_root_dir: Optional[str] = None, create_dirs: bool = True):
        """
        Initialize the abstract keyframe extractor.

        Args:
            keyframe_root_dir: Custom root directory for keyframes (optional)
            create_dirs: Whether to create directories on initialization (default: True)
        """
        self.keyframe_root_dir = Path(keyframe_root_dir or config.KEYFRAME_DIR)
        if create_dirs:
            self.keyframe_root_dir.mkdir(parents=True, exist_ok=True)
        self.supported_formats = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']

    def calculate_blur_score_from_file(self, image_path: str) -> float:
        """
        Calculate blur score from an image file using Laplacian variance.

        Args:
            image_path: Path to the image file

        Returns:
            Blur score (higher values indicate sharper images)

        Raises:
            FileNotFoundError: If image file cannot be found
            ValueError: If image cannot be processed
        """
        try:
            if not Path(image_path).exists():
                raise FileNotFoundError(f"Image file not found: {image_path}")

            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if image is None:
                raise ValueError(f"Could not load image: {image_path}")

            return self._calculate_blur_score(image)

        except Exception as e:
            logger.error("Failed to calculate blur score from file",
                         image_path=image_path, error=str(e))
            raise

    def validate_video_file(self, video_path: str) -> bool:
        """
        Validate that a video file exists and can be processed.

        Args:
            video_path: Path to the video file

        Returns:
            True if video is valid and can be processed, False otherwise
        """
        try:
            path = Path(video_path)

            # Check if file exists
            if not path.exists():
                logger.warning("Video file does not exist", video_path=video_path)
                return False

            # Check if file has supported extension
            if path.suffix.lower() not in self.supported_formats:
                logger.warning("Unsupported video format",
                               video_path=video_path,
                               format=path.suffix,
                               supported_formats=self.supported_formats)
                return False

            # Check if file is not empty
            if path.stat().st_size == 0:
                logger.warning("Video file is empty", video_path=video_path)
                return False

            # Try to open with OpenCV
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.warning("Cannot open video file with OpenCV", video_path=video_path)
                cap.release()
                return False

            # Check if video has frames
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()

            if frame_count <= 0:
                logger.warning("Video file has no frames", video_path=video_path)
                return False

            return True

        except Exception as e:
            logger.error("Error validating video file", video_path=video_path, error=str(e))
            return False

    def get_video_duration(self, video_path: str) -> float:
        """
        Get the duration of a video file in seconds.

        Args:
            video_path: Path to the video file

        Returns:
            Duration in seconds

        Raises:
            FileNotFoundError: If video file cannot be found
            ValueError: If video cannot be processed
        """
        try:
            if not Path(video_path).exists():
                raise FileNotFoundError(f"Video file not found: {video_path}")

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Cannot open video file: {video_path}")

            try:
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

                if fps <= 0:
                    raise ValueError(f"Invalid FPS value: {fps}")

                duration = frame_count / fps
                return duration

            finally:
                cap.release()

        except Exception as e:
            logger.error("Failed to get video duration", video_path=video_path, error=str(e))
            raise

    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported video formats.

        Returns:
            List of supported file extensions
        """
        return self.supported_formats.copy()

    def cleanup_extracted_frames(self, video_id: str) -> bool:
        """
        Clean up extracted frames for a specific video.

        Args:
            video_id: Unique identifier for the video

        Returns:
            True if cleanup was successful, False otherwise
        """
        try:
            keyframe_dir = self.keyframe_root_dir / video_id
            if keyframe_dir.exists():
                shutil.rmtree(keyframe_dir)
                logger.info("Cleaned up keyframes", video_id=video_id, directory=str(keyframe_dir))
                return True
            else:
                logger.debug("No keyframes directory to clean up", video_id=video_id)
                return True

        except Exception as e:
            logger.error("Failed to cleanup keyframes", video_id=video_id, error=str(e))
            return False

    def _validate_inputs(self, video_id: str, local_path: Optional[str]) -> bool:
        """
        Validate input parameters for keyframe extraction.

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

        return self.validate_video_file(local_path)

    def _create_keyframe_directory(self, video_id: str) -> Optional[Path]:
        """
        Create directory for storing keyframes.

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

    def _calculate_blur_score(self, image: np.ndarray) -> float:
        """
        Calculate blur score using Laplacian variance.

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

    def _get_video_properties(self, cap: cv2.VideoCapture, video_id: str) -> VideoProperties:
        """
        Extract video properties from OpenCV VideoCapture object.

        Args:
            cap: OpenCV VideoCapture object
            video_id: Video identifier for logging

        Returns:
            VideoProperties object containing video metadata

        Raises:
            ValueError: If video properties cannot be extracted
        """
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            if fps <= 0:
                raise ValueError(f"Invalid FPS value: {fps}")

            duration = total_frames / fps

            logger.debug("Video properties extracted",
                         video_id=video_id,
                         fps=fps,
                         total_frames=total_frames,
                         duration=duration,
                         resolution=f"{width}x{height}")

            # Import VideoProperties here to avoid circular imports
            from models.video import VideoProperties
            return VideoProperties(
                fps=fps,
                total_frames=total_frames,
                duration=duration,
                width=width,
                height=height
            )

        except Exception as e:
            logger.error("Failed to extract video properties",
                         video_id=video_id,
                         error=str(e))
            raise ValueError(f"Could not extract video properties: {str(e)}")

    def _save_frame(self, frame: np.ndarray, frame_path: str, quality: int = 95) -> bool:
        """
        Save a video frame as JPEG image.

        Args:
            frame: OpenCV frame array
            frame_path: Path where to save the frame
            quality: JPEG quality (0-100)

        Returns:
            True if frame was saved successfully, False otherwise
        """
        try:
            # Ensure directory exists
            Path(frame_path).parent.mkdir(parents=True, exist_ok=True)

            # Save frame with specified quality
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
            success = cv2.imwrite(frame_path, frame, encode_params)

            if not success:
                logger.error("Failed to save frame", frame_path=frame_path)
                return False

            # Verify file was created and is not empty
            if not Path(frame_path).exists() or Path(frame_path).stat().st_size == 0:
                logger.error("Saved frame is empty or missing", frame_path=frame_path)
                return False

            logger.debug("Frame saved successfully", frame_path=frame_path)
            return True

        except Exception as e:
            logger.error("Error saving frame", frame_path=frame_path, error=str(e))
            return False

    def _seek_to_timestamp(self, cap: cv2.VideoCapture, timestamp: float, fps: float) -> bool:
        """
        Seek video capture to a specific timestamp.

        Args:
            cap: OpenCV VideoCapture object
            timestamp: Target timestamp in seconds
            fps: Video frame rate

        Returns:
            True if seek was successful, False otherwise
        """
        try:
            frame_number = int(timestamp * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

            # Verify the seek was successful
            actual_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
            if abs(actual_frame - frame_number) > 5:  # Allow small tolerance
                logger.warning("Seek accuracy issue",
                               target_frame=frame_number,
                               actual_frame=actual_frame,
                               timestamp=timestamp)

            return True

        except Exception as e:
            logger.error("Failed to seek to timestamp",
                         timestamp=timestamp,
                         error=str(e))
            return False

    def _generate_frame_filename(self, video_id: str, timestamp: float, format: str = "jpg") -> str:
        """
        Generate a consistent filename for extracted frames.

        Args:
            video_id: Video identifier
            timestamp: Frame timestamp in seconds
            format: Image format (default: jpg)

        Returns:
            Filename string
        """
        # Format timestamp to avoid floating point precision issues
        timestamp_str = f"{timestamp:.2f}".replace(".", "_")
        return f"frame_{timestamp_str}s.{format}"

    async def extract_keyframes(
        self,
        video_url: str,
        video_id: str,
        local_path: Optional[str] = None
    ) -> List[Tuple[float, str]]:
        """
        Template method for extracting keyframes with common workflow.

        This method implements the common extraction workflow that most extractors will use:
        1. Validate inputs
        2. Create keyframe directory
        3. Delegate to subclass-specific extraction logic
        4. Handle errors gracefully

        Subclasses should override _extract_frames_from_video() to implement
        their specific extraction strategy.
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

            # If no keyframes were extracted but the directory was created, clean it up
            # This prevents empty directories from accumulating
            if not keyframes and keyframe_dir.exists():
                logger.debug("No keyframes extracted, cleaning up empty directory", video_id=video_id)
                try:
                    shutil.rmtree(keyframe_dir)
                except Exception as cleanup_exc:
                    logger.warning("Failed to cleanup empty keyframes directory",
                                   video_id=video_id,
                                   directory=str(keyframe_dir),
                                   error=str(cleanup_exc))

            return keyframes

        except Exception as e:
            logger.error("Failed to extract keyframes",
                         video_id=video_id,
                         local_path=local_path,
                         error=str(e))

            # Clean up directory on failure
            if keyframe_dir and keyframe_dir.exists():
                try:
                    shutil.rmtree(keyframe_dir)
                except Exception as cleanup_exc:
                    logger.warning("Failed to cleanup keyframes directory after error",
                                   video_id=video_id,
                                   directory=str(keyframe_dir),
                                   error=str(cleanup_exc))

            return []

    @abstractmethod
    async def _extract_frames_from_video(
        self,
        video_path: str,
        keyframe_dir: Path,
        video_id: str
    ) -> List[Tuple[float, str]]:
        """
        Abstract method for subclass-specific frame extraction logic.

        Args:
            video_path: Path to the video file
            keyframe_dir: Directory to save extracted frames
            video_id: Video identifier for logging

        Returns:
            List of tuples containing (timestamp, frame_path)

        Raises:
            ValueError: If video cannot be opened or processed
        """
        pass
