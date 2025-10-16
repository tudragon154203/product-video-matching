from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class Product(BaseModel):
    product_id: str
    src: str  # 'amazon' or 'ebay'
    asin_or_itemid: str
    title: Optional[str] = None
    brand: Optional[str] = None
    url: Optional[str] = None
    marketplace: str  # 'us', 'de', 'au'
    job_id: Optional[str] = None
    created_at: Optional[datetime] = None


class ProductImage(BaseModel):
    img_id: str
    product_id: str
    local_path: str
    masked_local_path: Optional[str] = None
    emb_rgb: Optional[List[float]] = None
    emb_gray: Optional[List[float]] = None
    kp_blob_path: Optional[str] = None
    phash: Optional[int] = None
    created_at: Optional[datetime] = None


class Video(BaseModel):
    video_id: str
    platform: str  # 'youtube', 'bilibili'
    url: str
    title: Optional[str] = None
    duration_s: Optional[int] = None
    published_at: Optional[datetime] = None
    job_id: Optional[str] = None
    created_at: Optional[datetime] = None
    download_url: Optional[str] = None
    local_path: Optional[str] = None
    has_download: bool = False
    keyframes: Optional[List[str]] = None


class VideoFrame(BaseModel):
    frame_id: str
    video_id: str
    ts: float  # Timestamp in video
    local_path: str
    masked_local_path: Optional[str] = None
    emb_rgb: Optional[List[float]] = None
    emb_gray: Optional[List[float]] = None
    kp_blob_path: Optional[str] = None
    created_at: Optional[datetime] = None


class Match(BaseModel):
    match_id: str
    job_id: str
    product_id: str
    video_id: str
    best_img_id: str
    best_frame_id: str
    ts: Optional[float] = None
    score: float
    evidence_path: Optional[str] = None
    created_at: Optional[datetime] = None