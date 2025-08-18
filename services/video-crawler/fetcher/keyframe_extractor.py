import asyncio
import subprocess
from pathlib import Path
from typing import List, Tuple
import cv2
import numpy as np
import logging
from common_py.logging_config import configure_logging

logger = configure_logging("video-crawler")


class KeyframeExtractor:
    """Handles keyframe extraction from videos"""
    
    def __init__(self, data_root: str):
        self.data_root = Path(data_root)
        self.videos_dir = self.data_root / "videos"
        self.videos_dir.mkdir(parents=True, exist_ok=True)
    
    async def extract_keyframes(self, video_url: str, video_id: str) -> List[Tuple[float, str]]:
        """
        Extract keyframes from video (mock implementation with dummy frames)
        In production, this would download the video and extract real frames
        """
        try:
            # Create video directory
            video_dir = self.videos_dir / video_id / "frames"
            video_dir.mkdir(parents=True, exist_ok=True)
            
            # For MVP, create dummy frames instead of downloading real video
            keyframes = []
            
            # Generate 5 dummy frames at different timestamps
            timestamps = [10.0, 30.0, 60.0, 90.0, 120.0]
            
            for i, ts in enumerate(timestamps):
                frame_path = video_dir / f"frame_{i}.jpg"
                
                # Create a dummy frame (colored rectangle with timestamp)
                await self.create_dummy_frame(frame_path, ts, i)
                
                keyframes.append((ts, str(frame_path)))
            
            logger.info("Extracted keyframes", video_id=video_id, count=len(keyframes))
            return keyframes
            
        except Exception as e:
            logger.error("Failed to extract keyframes", video_id=video_id, error=str(e))
            return []
    
    async def create_dummy_frame(self, frame_path: Path, timestamp: float, frame_index: int):
        """Create a dummy frame for MVP testing"""
        try:
            # Create a colored image with some variation
            height, width = 480, 640
            
            # Different colors for different frames
            colors = [
                (255, 100, 100),  # Red-ish
                (100, 255, 100),  # Green-ish
                (100, 100, 255),  # Blue-ish
                (255, 255, 100),  # Yellow-ish
                (255, 100, 255),  # Magenta-ish
            ]
            
            color = colors[frame_index % len(colors)]
            
            # Create base image
            image = np.full((height, width, 3), color, dtype=np.uint8)
            
            # Add some noise for variation
            noise = np.random.randint(0, 50, (height, width, 3), dtype=np.uint8)
            image = cv2.add(image, noise)
            
            # Add timestamp text
            cv2.putText(image, f"t={timestamp:.1f}s", (50, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # Add frame index
            cv2.putText(image, f"Frame {frame_index}", (50, 100), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # Save image
            cv2.imwrite(str(frame_path), image)
            
        except Exception as e:
            logger.error("Failed to create dummy frame", frame_path=str(frame_path), error=str(e))
    
    def calculate_blur_score(self, image_path: str) -> float:
        """Calculate blur score using Laplacian variance"""
        try:
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if image is None:
                return 0.0
            
            # Calculate Laplacian variance
            laplacian = cv2.Laplacian(image, cv2.CV_64F)
            variance = laplacian.var()
            
            return variance
            
        except Exception as e:
            logger.error("Failed to calculate blur score", image_path=image_path, error=str(e))
            return 0.0