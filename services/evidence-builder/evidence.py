import cv2
import numpy as np
from pathlib import Path
from typing import Optional
from common_py.logging_config import configure_logging
from PIL import Image, ImageDraw, ImageFont
from evidence_image_renderer import EvidenceImageRenderer

logger = configure_logging("evidence-builder:evidence")


class EvidenceGenerator:
    """Generates visual evidence images for matches"""
    
    def __init__(self, data_root: str):
        self.data_root = Path(data_root)
        self.evidence_dir = self.data_root / "evidence"
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.image_renderer = EvidenceImageRenderer()
    
    def create_evidence(self, image_path: str, frame_path: str, 
                            img_id: str, frame_id: str, score: float, 
                            timestamp: float, kp_img_path: Optional[str] = None, 
                            kp_frame_path: Optional[str] = None) -> Optional[str]:
        """Create evidence image showing the match"""
        try:
            # Generate evidence filename
            evidence_filename = f"{img_id}_{frame_id}_evidence.jpg"
            evidence_path = self.evidence_dir / evidence_filename
            
            # Load images
            product_img = cv2.imread(image_path)
            frame_img = cv2.imread(frame_path)
            
            if product_img is None or frame_img is None:
                logger.error("Failed to load images", 
                           image_path=image_path, frame_path=frame_path)
                return None
            
            # Create side-by-side comparison
            evidence_img = self.image_renderer.create_side_by_side_comparison(
                product_img, frame_img, score, timestamp, img_id, frame_id
            )
            
            # Add keypoint overlays if available
            if kp_img_path and kp_frame_path:
                evidence_img = self.add_keypoint_overlays(
                    evidence_img, product_img, frame_img, 
                    kp_img_path, kp_frame_path
                )
            
            # Save evidence image
            cv2.imwrite(str(evidence_path), evidence_img)
            
            logger.info("Created evidence image", 
                       evidence_path=str(evidence_path),
                       score=score)
            
            return str(evidence_path)
            
        except Exception as e:
            logger.error("Failed to create evidence", 
                        img_id=img_id, frame_id=frame_id, error=str(e))
            return None
    
    def add_keypoint_overlays(self, evidence_img: np.ndarray, 
                                  product_img: np.ndarray, frame_img: np.ndarray,
                                  kp_img_path: str, kp_frame_path: str) -> np.ndarray:
        """Add keypoint match overlays (mock implementation)"""
        try:
            # For MVP, add mock keypoint indicators
            # In production, this would load actual keypoints and draw matches
            
            # Get image dimensions in the evidence
            height, width = evidence_img.shape[:2]
            
            # Add some mock keypoint circles
            # Left side (product image area)
            left_center_x = width // 4
            center_y = height // 2
            
            # Right side (frame image area)
            right_center_x = 3 * width // 4
            
            # Draw mock keypoints
            for i in range(5):  # 5 mock keypoints
                # Random positions around centers
                left_x = left_center_x + np.random.randint(-50, 50)
                left_y = center_y + np.random.randint(-50, 50)
                right_x = right_center_x + np.random.randint(-50, 50)
                right_y = center_y + np.random.randint(-50, 50)
                
                # Draw keypoints
                cv2.circle(evidence_img, (left_x, left_y), 3, (0, 0, 255), -1)  # Red circles
                cv2.circle(evidence_img, (right_x, right_y), 3, (0, 0, 255), -1)
                
                # Draw connection line
                cv2.line(evidence_img, (left_x, left_y), (right_x, right_y), (255, 0, 0), 1)  # Blue lines
            
            # Add legend
            legend_y = height - 30
            cv2.putText(evidence_img, "Red: Keypoints, Blue: Matches", 
                       (20, legend_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            
            return evidence_img
            
        except Exception as e:
            logger.error("Failed to add keypoint overlays", error=str(e))
            return evidence_img
