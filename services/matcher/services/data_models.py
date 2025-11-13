from pydantic import BaseModel, Field
from typing import List, Dict, Any


class Product(BaseModel):
    """Represents an e-commerce product with an associated image."""
    product_id: str = Field(..., description="Unique identifier for the product")
    image_url: str = Field(..., description="URL to the product image")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional product information")


class VideoFrame(BaseModel):
    """Represents a single frame extracted from a video."""
    frame_id: str = Field(..., description="Unique identifier for the video frame")
    video_id: str = Field(..., description="Identifier for the video the frame belongs to")
    timestamp: float = Field(..., description="Timestamp of the frame within the video")
    image_url: str = Field(..., description="URL to the video frame image")


class MatchResult(BaseModel):
    """Contains the match score, bounding box, and confidence level for a product-video frame match."""
    product_id: str = Field(..., description="ID of the matched product")
    frame_id: str = Field(..., description="ID of the video frame")
    match_score: float = Field(..., description="Overall match score")
    bounding_box: List[float] = Field(..., min_items=4, max_items=4,
                                      description="[x_min, y_min, x_max, y_max] coordinates of the bounding box")
    confidence_level: float = Field(..., description="Confidence level of the match")
