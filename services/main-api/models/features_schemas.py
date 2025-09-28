from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class FeatureProgress(BaseModel):
    done: int
    percent: float


class ProductImagesFeatures(BaseModel):
    total: int
    segment: FeatureProgress
    embedding: FeatureProgress
    keypoints: FeatureProgress


class VideoFramesFeatures(BaseModel):
    total: int
    segment: FeatureProgress
    embedding: FeatureProgress
    keypoints: FeatureProgress


class FeaturesSummaryResponse(BaseModel):
    job_id: str
    product_images: ProductImagesFeatures
    video_frames: VideoFramesFeatures
    updated_at: Optional[datetime] = None


class FeaturePaths(BaseModel):
    segment: Optional[str] = None
    embedding: Optional[str] = None
    keypoints: Optional[str] = None


class ProductImageFeatureItem(BaseModel):
    img_id: str
    product_id: str
    has_segment: bool
    has_embedding: bool
    has_keypoints: bool
    paths: FeaturePaths
    updated_at: Optional[datetime] = None


class ProductImageFeaturesResponse(BaseModel):
    items: list[ProductImageFeatureItem]
    total: int
    limit: int
    offset: int


class VideoFrameFeatureItem(BaseModel):
    frame_id: str
    video_id: str
    ts: float
    has_segment: bool
    has_embedding: bool
    has_keypoints: bool
    paths: FeaturePaths
    updated_at: Optional[datetime] = None


class VideoFrameFeaturesResponse(BaseModel):
    items: list[VideoFrameFeatureItem]
    total: int
    limit: int
    offset: int
