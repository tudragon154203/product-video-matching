"""
Results schema definitions for the Main API.
Contains Pydantic models for results-related response validation
and documentation.
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class ProductResponse(BaseModel):
    """Product response schema for results"""
    product_id: str = Field(..., description="Unique product identifier")
    src: Optional[str] = Field(
        None, description="Product source (amazon, ebay, etc.)")
    asin_or_itemid: Optional[str] = Field(
        None, description="ASIN or item ID from source")
    title: Optional[str] = Field(None, description="Product title")
    brand: Optional[str] = Field(None, description="Product brand")
    url: Optional[str] = Field(None, description="Product URL")
    created_at: str = Field(..., description="Product creation timestamp")
    image_count: int = Field(..., description="Number of product images")


class VideoResponse(BaseModel):
    """Video response schema for results"""
    video_id: str = Field(..., description="Unique video identifier")
    platform: Optional[str] = Field(
        None, description="Video platform (youtube, etc.)")
    url: Optional[str] = Field(None, description="Video URL")
    title: Optional[str] = Field(None, description="Video title")
    duration_s: Optional[int] = Field(
        None, description="Video duration in seconds")
    published_at: Optional[str] = Field(
        None, description="Video publication timestamp")
    created_at: str = Field(..., description="Video creation timestamp")
    frame_count: int = Field(..., description="Number of video frames")


class MatchResponse(BaseModel):
    """Match response schema for results list"""
    match_id: str = Field(..., description="Unique match identifier")
    job_id: str = Field(..., description="Job identifier")
    product_id: str = Field(..., description="Product identifier")
    video_id: str = Field(..., description="Video identifier")
    best_img_id: Optional[str] = Field(
        None, description="Best matching image ID")
    best_frame_id: Optional[str] = Field(
        None, description="Best matching frame ID")
    ts: Optional[float] = Field(None, description="Timestamp in video")
    score: float = Field(..., description="Match confidence score")
    evidence_path: Optional[str] = Field(
        None, description="Path to evidence image")
    evidence_url: Optional[str] = Field(
        None, description="Public URL to evidence image")
    created_at: str = Field(..., description="Match creation timestamp")

    # Enriched fields
    product_title: Optional[str] = Field(None, description="Product title")
    video_title: Optional[str] = Field(None, description="Video title")
    video_platform: Optional[str] = Field(None, description="Video platform")


class MatchDetailResponse(BaseModel):
    """Detailed match response schema"""
    match_id: str = Field(..., description="Unique match identifier")
    job_id: str = Field(..., description="Job identifier")
    best_img_id: Optional[str] = Field(
        None, description="Best matching image ID")
    best_frame_id: Optional[str] = Field(
        None, description="Best matching frame ID")
    ts: Optional[float] = Field(None, description="Timestamp in video")
    score: float = Field(..., description="Match confidence score")
    evidence_path: Optional[str] = Field(
        None, description="Path to evidence image")
    evidence_url: Optional[str] = Field(
        None, description="Public URL to evidence image")
    created_at: str = Field(..., description="Match creation timestamp")

    product: ProductResponse = Field(..., description="Product details")
    video: VideoResponse = Field(..., description="Video details")


class StatsResponse(BaseModel):
    """System statistics response schema"""
    products: int = Field(..., description="Total number of products")
    product_images: int = Field(...,
                                description="Total number of product images")
    videos: int = Field(..., description="Total number of videos")
    video_frames: int = Field(..., description="Total number of video frames")
    matches: int = Field(..., description="Total number of matches")
    jobs: int = Field(..., description="Total number of jobs")


class MatchListResponse(BaseModel):
    """Schema for match list response with pagination"""
    items: List[MatchResponse] = Field(..., description="List of matches")
    total: int = Field(..., description="Total number of matches")
    limit: int = Field(..., description="Number of items per page")
    offset: int = Field(..., description="Number of items skipped")


class EvidenceResponse(BaseModel):
    """Evidence image response schema"""
    evidence_path: str = Field(..., description="Path to evidence image file")
    evidence_url: Optional[str] = Field(
        None, description="Public URL to evidence image")
