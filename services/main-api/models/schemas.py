from pydantic import BaseModel

class StartJobRequest(BaseModel):
    query: str
    top_amz: int
    top_ebay: int
    platforms: list
    recency_days: int

class StartJobResponse(BaseModel):
    job_id: str
    status: str

from datetime import datetime
from typing import Optional

class JobStatusResponse(BaseModel):
    job_id: str
    phase: str
    percent: float
    counts: dict
    updated_at: Optional[datetime] = None

class JobAssetTypes(BaseModel):
    """Schema for job asset types indicating which media types are present"""
    images: bool
    videos: bool
    
    @property
    def job_type(self) -> str:
        """Return the job type based on asset types"""
        if self.images and self.videos:
            return "mixed"
        elif self.images:
            return "product-only"
        elif self.videos:
            return "video-only"
        else:
            return "zero-asset"


class PreviewFrame(BaseModel):
    """Schema for video preview frame"""
    frame_id: str
    ts: float
    url: str
    segment_url: Optional[str] = None


class VideoItem(BaseModel):
    """Schema for video item in list response"""
    video_id: str
    platform: str
    url: str
    title: str
    duration_s: float
    frames_count: int
    updated_at: datetime
    preview_frame: Optional[PreviewFrame] = None
    first_keyframe_url: Optional[str] = None


class VideoListResponse(BaseModel):
    """Schema for video list response with pagination"""
    items: list[VideoItem]
    total: int
    limit: int
    offset: int


class FrameItem(BaseModel):
    """Schema for frame item in list response"""
    frame_id: str
    ts: float
    local_path: str
    url: Optional[str] = None  # New field for public URL
    updated_at: datetime


class FrameListResponse(BaseModel):
    """Schema for frame list response with pagination"""
    items: list[FrameItem]
    total: int
    limit: int
    offset: int


class ImageItem(BaseModel):
    """Schema for image item in list response"""
    img_id: str
    product_id: str
    local_path: str
    url: Optional[str] = None  # New field for public URL
    product_title: str
    updated_at: datetime


class ImageListResponse(BaseModel):
    """Schema for image list response with pagination"""
    items: list[ImageItem]
    total: int
    limit: int
    offset: int


class JobItem(BaseModel):
    """Schema for job item in list response"""
    job_id: str
    query: str
    industry: str
    phase: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class JobListResponse(BaseModel):
    """Schema for job list response with pagination"""
    items: list[JobItem]
    total: int
    limit: int
    offset: int


class ProductItem(BaseModel):
    """Schema for product item in list response"""
    product_id: str
    src: str
    asin_or_itemid: str
    title: Optional[str] = None
    brand: Optional[str] = None
    url: Optional[str] = None
    image_count: int
    created_at: datetime
    primary_image_url: Optional[str] = None


class ProductListResponse(BaseModel):
    """Schema for product list response with pagination"""
    items: list[ProductItem]
    total: int
    limit: int
    offset: int