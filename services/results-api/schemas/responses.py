from typing import Optional, List, Dict
from pydantic import BaseModel


class Pagination(BaseModel):
    """Pagination metadata for list responses"""
    total: int
    limit: int
    offset: int
    has_next: bool
    has_previous: bool


class BaseResponse(BaseModel):
    """Base response structure"""
    success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None


class ProductResponse(BaseModel):
    """Product response schema"""
    id: str
    name: str
    category: str
    price: Optional[float] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    created_at: str


class VideoResponse(BaseModel):
    """Video response schema"""
    id: str
    title: str
    url: str
    platform: str
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = None
    view_count: Optional[int] = None
    published_at: str


class MatchResponse(BaseModel):
    """Match response schema"""
    id: str
    product_id: str
    video_id: str
    similarity_score: float
    platform: str
    match_type: str
    evidence_path: Optional[str] = None
    created_at: str
    
    # Enriched fields
    product: Optional[ProductResponse] = None
    video: Optional[VideoResponse] = None


class ResultsListResponse(BaseModel):
    """Response for list of matching results"""
    success: bool
    data: List[MatchResponse]
    pagination: Pagination
    total_count: int


class StatsResponse(BaseModel):
    """Stats response schema"""
    total_products: int
    total_videos: int
    total_matches: int
    average_similarity_score: float
    top_industries: List[Dict[str, int]]


class HealthResponse(BaseModel):
    """Health check response schema"""
    status: str
    timestamp: str
    services: Dict[str, str]


class NotFoundResponse(BaseModel):
    """Not found error response"""
    success: bool = False
    error: str
    detail: str


class ServerErrorResponse(BaseModel):
    """Server error response schema"""
    success: bool = False
    error: str
    detail: str