from typing import Optional, List
from pydantic import BaseModel


class Product(BaseModel):
    """Product entity schema"""
    id: str
    name: str
    category: str
    price: Optional[float] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    created_at: str


class Video(BaseModel):
    """Video entity schema"""
    id: str
    title: str
    url: str
    platform: str
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = None
    view_count: Optional[int] = None
    published_at: str


class Match(BaseModel):
    """Match entity schema"""
    id: str
    product_id: str
    video_id: str
    similarity_score: float
    platform: str
    match_type: str
    evidence_path: Optional[str] = None
    created_at: str


class MatchWithDetails(BaseModel):
    """Match entity with related data"""
    id: str
    product_id: str
    video_id: str
    similarity_score: float
    platform: str
    match_type: str
    evidence_path: Optional[str] = None
    created_at: str
    
    product: Optional[Product] = None
    video: Optional[Video] = None