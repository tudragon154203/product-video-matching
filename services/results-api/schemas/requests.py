"""
Request schema definitions for the Results API.
Contains Pydantic models for request validation and documentation.
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ResultsQueryParams(BaseModel):
    """Query parameters for getting matching results"""
    industry: Optional[str] = Field(
        None, 
        description="Filter results by industry",
        max_length=100
    )
    min_score: Optional[float] = Field(
        None, 
        description="Minimum match score (0.0 to 1.0)",
        ge=0.0,
        le=1.0
    )
    job_id: Optional[str] = Field(
        None, 
        description="Filter results by job ID",
        max_length=50
    )
    limit: int = Field(
        100, 
        description="Maximum number of results to return",
        ge=1,
        le=1000
    )
    offset: int = Field(
        0, 
        description="Number of results to skip",
        ge=0
    )
    
    @field_validator('industry')
    @classmethod
    def validate_industry(cls, v):
        if v is not None:
            return v.strip()
        return v
    
    @field_validator('job_id')
    @classmethod
    def validate_job_id(cls, v):
        if v is not None:
            return v.strip()
        return v


class ProductPathParams(BaseModel):
    """Path parameters for product endpoints"""
    product_id: str = Field(
        ..., 
        description="Product ID",
        min_length=1,
        max_length=100
    )


class VideoPathParams(BaseModel):
    """Path parameters for video endpoints"""
    video_id: str = Field(
        ..., 
        description="Video ID",
        min_length=1,
        max_length=100
    )


class MatchPathParams(BaseModel):
    """Path parameters for match endpoints"""
    match_id: str = Field(
        ..., 
        description="Match ID",
        min_length=1,
        max_length=100
    )


class EvidencePathParams(BaseModel):
    """Path parameters for evidence endpoints"""
    match_id: str = Field(
        ..., 
        description="Match ID for evidence retrieval",
        min_length=1,
        max_length=100
    )