from typing import Optional
from pydantic import BaseModel


class GetResultsRequest(BaseModel):
    """Request parameters for getting matching results"""
    industry: Optional[str] = None
    min_score: Optional[float] = None
    job_id: Optional[str] = None
    limit: int = 100
    offset: int = 0


class GetProductRequest(BaseModel):
    """Request parameters for getting product details"""
    product_id: str


class GetVideoRequest(BaseModel):
    """Request parameters for getting video details"""
    video_id: str


class GetMatchRequest(BaseModel):
    """Request parameters for getting match details"""
    match_id: str


class GetEvidenceRequest(BaseModel):
    """Request parameters for getting evidence image"""
    match_id: str