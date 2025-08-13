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