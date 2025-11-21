from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class MatchingSummaryResponse(BaseModel):
    """Response schema for matching phase summary"""
    job_id: str
    status: str = Field(
        ...,
        description="Status: pending | running | completed | failed"
    )
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_event_at: Optional[datetime] = None
    candidates_total: int = 0
    candidates_processed: int = 0
    vector_pass_total: int = 0
    vector_pass_done: int = 0
    ransac_checked: int = 0
    matches_found: int = 0
    matches_with_evidence: int = 0
    avg_score: Optional[float] = None
    p90_score: Optional[float] = None
    queue_depth: int = 0
    eta_seconds: Optional[int] = None
    blockers: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True
