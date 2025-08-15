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

class JobStatusResponse(BaseModel):
    job_id: str
    phase: str
    percent: float
    counts: dict

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