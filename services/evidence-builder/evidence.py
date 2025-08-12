import cv2
import numpy as np
from pathlib import Path
from typing import Optional
import structlog
from PIL import Image, ImageDraw, ImageFont

logger = structlog.get_logger()


class EvidenceGenerator:
    """Generates visual evidence images for matches"""
    
    def __init__(self, data_root: str):
        self.data_root = Path(data_root)
        self.evidence_dir = self.data_root / "evidence"
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_evidence(self, image_path: str, frame_path: str, 
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
            evidence_img = await self.create_side_by_side_comparison(
                product_img, frame_img, score, timestamp, img_id, frame_id
            )
            
            # Add keypoint overlays if available
            if kp_img_path and kp_frame_path:
                evidence_img = await self.add_keypoint_overlays(
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
    
    async def create_side_by_side_comparison(self, product_img: np.ndarray, 
                                           frame_img: np.ndarray, score: float, 
                                           timestamp: float, img_id: str, 
                                           frame_id: str) -> np.ndarray:
        """Create side-by-side comparison image"""
        try:
            # Resize images to same height
            target_height = 400
            
            # Resize product image
            h1, w1 = product_img.shape[:2]
            new_w1 = int(w1 * target_height / h1)
            product_resized = cv2.resize(product_img, (new_w1, target_height))
            
            # Resize frame image
            h2, w2 = frame_img.shape[:2]
            new_w2 = int(w2 * target_height / h2)
            frame_resized = cv2.resize(frame_img, (new_w2, target_height))
            
            # Create combined image with padding
            padding = 20
            header_height = 80
            footer_height = 60
            
            total_width = new_w1 + new_w2 + padding * 3
            total_height = target_height + header_height + footer_height
            
            # Create white background
            combined = np.ones((total_height, total_width, 3), dtype=np.uint8) * 255
            
            # Place images
            y_offset = header_height
            combined[y_offset:y_offset+target_height, padding:padding+new_w1] = product_resized
            combined[y_offset:y_offset+target_height, padding*2+new_w1:padding*2+new_w1+new_w2] = frame_resized
            
            # Add text labels
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.7
            color = (0, 0, 0)  # Black
            thickness = 2
            
            # Header
            header_text = f"Product-Video Match (Score: {score:.3f})"
            cv2.putText(combined, header_text, (padding, 30), font, font_scale, color, thickness)
            
            # Image labels
            cv2.putText(combined, "Product Image", (padding, y_offset - 10), font, 0.6, color, 1)
            cv2.putText(combined, f"Video Frame (t={timestamp:.1f}s)", 
                       (padding*2 + new_w1, y_offset - 10), font, 0.6, color, 1)
            
            # Footer with IDs
            footer_y = y_offset + target_height + 30
            cv2.putText(combined, f"Image ID: {img_id}", (padding, footer_y), font, 0.5, color, 1)
            cv2.putText(combined, f"Frame ID: {frame_id}", (padding*2 + new_w1, footer_y), font, 0.5, color, 1)
            
            # Add border around images
            cv2.rectangle(combined, (padding-2, y_offset-2), 
                         (padding+new_w1+2, y_offset+target_height+2), (0, 255, 0), 2)
            cv2.rectangle(combined, (padding*2+new_w1-2, y_offset-2), 
                         (padding*2+new_w1+new_w2+2, y_offset+target_height+2), (0, 255, 0), 2)
            
            return combined
            
        except Exception as e:
            logger.error("Failed to create side-by-side comparison", error=str(e))
            # Return simple concatenation as fallback
            return np.hstack([product_img, frame_img])
    
    async def add_keypoint_overlays(self, evidence_img: np.ndarray, 
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