"""
Entity schema definitions for the Results API.
Contains core domain models and database entity representations.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ProductEntity(BaseModel):
    """Product entity schema matching database structure"""
    product_id: str = Field(..., description="Unique product identifier")
    src: Optional[str] = Field(None, description="Product source (amazon, ebay, etc.)")
    asin_or_itemid: Optional[str] = Field(None, description="ASIN or item ID from source")
    title: Optional[str] = Field(None, description="Product title")
    brand: Optional[str] = Field(None, description="Product brand")
    url: Optional[str] = Field(None, description="Product URL")
    created_at: Optional[datetime] = Field(None, description="Product creation timestamp")


class VideoEntity(BaseModel):
    """Video entity schema matching database structure"""
    video_id: str = Field(..., description="Unique video identifier")
    platform: Optional[str] = Field(None, description="Video platform (youtube, etc.)")
    url: Optional[str] = Field(None, description="Video URL")
    title: Optional[str] = Field(None, description="Video title")
    duration_s: Optional[int] = Field(None, description="Video duration in seconds")
    published_at: Optional[datetime] = Field(None, description="Video publication timestamp")
    created_at: Optional[datetime] = Field(None, description="Video creation timestamp")


class MatchEntity(BaseModel):
    """Match entity schema matching database structure"""
    match_id: str = Field(..., description="Unique match identifier")
    job_id: str = Field(..., description="Job identifier")
    product_id: str = Field(..., description="Product identifier")
    video_id: str = Field(..., description="Video identifier")
    best_img_id: Optional[str] = Field(None, description="Best matching image ID")
    best_frame_id: Optional[str] = Field(None, description="Best matching frame ID")
    ts: Optional[float] = Field(None, description="Timestamp in video")
    score: float = Field(..., description="Match confidence score")
    evidence_path: Optional[str] = Field(None, description="Path to evidence image")
    created_at: Optional[datetime] = Field(None, description="Match creation timestamp")


class JobEntity(BaseModel):
    """Job entity schema matching database structure"""
    job_id: str = Field(..., description="Unique job identifier")
    status: Optional[str] = Field(None, description="Job status")
    created_at: Optional[datetime] = Field(None, description="Job creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Job last update timestamp")


class ProductImageEntity(BaseModel):
    """Product image entity schema"""
    image_id: str = Field(..., description="Unique image identifier")
    product_id: str = Field(..., description="Product identifier")
    image_path: Optional[str] = Field(None, description="Path to image file")
    created_at: Optional[datetime] = Field(None, description="Image creation timestamp")


class VideoFrameEntity(BaseModel):
    """Video frame entity schema"""
    frame_id: str = Field(..., description="Unique frame identifier")
    video_id: str = Field(..., description="Video identifier")
    frame_path: Optional[str] = Field(None, description="Path to frame file")
    timestamp: Optional[float] = Field(None, description="Frame timestamp in video")
    created_at: Optional[datetime] = Field(None, description="Frame creation timestamp")