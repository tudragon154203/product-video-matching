# Sprint 11 - Backend: Matching Phase Summary API

## Document Status
- **Type**: Backend Implementation Document
- **Sprint**: 11
- **Last Updated**: 2025-11-21
- **Status**: Implemented

## 1. Overview
The Matching Summary API provides aggregated statistics and health signals for the matching phase of a job. It enables the frontend to display real-time progress without heavy client-side aggregation.

## 2. API Specification

### 2.1 Endpoint
```
GET /jobs/{job_id}/matching/summary
```

### 2.2 Query Parameters
- `force_refresh` (optional, boolean, default: false)
  - Forces refresh from database
  - Bypasses any caching (if implemented in future)

### 2.3 Response Schema
**MatchingSummaryResponse** (`models/matching_schemas.py`)
```python
{
  "job_id": "uuid",
  "status": "pending | running | completed | failed",
  "started_at": "2025-11-21T10:00:00Z",  # Job created_at
  "completed_at": "2025-11-21T10:15:00Z",  # Job updated_at if completed
  "last_event_at": "2025-11-21T10:14:30Z",  # Job updated_at
  "candidates_total": 180,  # product_images * video_frames
  "candidates_processed": 75,  # Estimated based on phase/matches
  "vector_pass_total": 180,  # Same as candidates_total
  "vector_pass_done": 75,  # Same as candidates_processed
  "ransac_checked": 18,  # Same as matches_found
  "matches_found": 18,  # COUNT(*) FROM matches
  "matches_with_evidence": 6,  # COUNT(*) WHERE evidence_path IS NOT NULL
  "avg_score": 0.64,  # AVG(score) FROM matches
  "p90_score": 0.82,  # PERCENTILE_CONT(0.9) FROM matches
  "queue_depth": 0,  # Currently always 0 (placeholder)
  "eta_seconds": 210,  # Calculated from elapsed time and progress
  "blockers": []  # Currently always empty (placeholder)
}
```

### 2.4 Status Codes
- `200 OK`: Summary returned successfully
- `404 Not Found`: Job does not exist
- `500 Internal Server Error`: Database or calculation error

## 3. Implementation

### 3.1 Service Layer
**MatchingService** (`services/matching/matching_service.py`)

#### Key Methods
```python
async def get_matching_summary(
    self,
    job_id: str,
    force_refresh: bool = False
) -> Optional[MatchingSummaryResponse]
```

#### Status Determination Logic
```python
if phase == 'matching':
    status = 'running'
elif phase in ('evidence', 'completed'):
    status = 'completed'
elif phase == 'failed':
    status = 'failed'
else:
    status = 'pending'
```

### 3.2 Database Queries

#### 3.2.1 Job Status Query
```sql
SELECT job_id, phase, created_at, updated_at
FROM jobs
WHERE job_id = $1
```

#### 3.2.2 Matches Count
```sql
SELECT COUNT(*) as count
FROM matches
WHERE job_id = $1
```

#### 3.2.3 Evidence Coverage
```sql
SELECT COUNT(*) as count
FROM matches
WHERE job_id = $1 AND evidence_path IS NOT NULL
```

#### 3.2.4 Score Statistics
```sql
SELECT 
    AVG(score) as avg_score,
    PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY score) as p90_score
FROM matches
WHERE job_id = $1
```

#### 3.2.5 Product Images Count
```sql
SELECT COUNT(DISTINCT pi.img_id) as count
FROM product_images pi
JOIN products p ON pi.product_id = p.product_id
WHERE p.job_id = $1
```

#### 3.2.6 Video Frames Count
```sql
SELECT COUNT(DISTINCT vf.frame_id) as count
FROM video_frames vf
JOIN job_videos jv ON vf.video_id = jv.video_id
WHERE jv.job_id = $1
```

### 3.3 Calculation Logic

#### 3.3.1 Candidates Total
```python
candidates_total = product_images_count * video_frames_count
```
- Represents all possible product-frame pairs
- Used as denominator for progress calculation

#### 3.3.2 Candidates Processed (Estimation)
```python
if status == 'completed':
    candidates_processed = candidates_total
elif status == 'running' and candidates_total > 0:
    if matches_found > 0:
        # Rough estimate: assume 100 candidates per match
        candidates_processed = min(matches_found * 100, candidates_total)
    else:
        # Early in processing, assume 10%
        candidates_processed = int(candidates_total * 0.1)
```
**Note**: This is an approximation. Actual processing count would require event tracking.

#### 3.3.3 ETA Calculation
```python
if status == 'running' and candidates_processed > 0:
    elapsed = (last_event_at - created_at).total_seconds()
    if elapsed > 0 and candidates_processed > 0:
        rate = candidates_processed / elapsed
        remaining = candidates_total - candidates_processed
        if rate > 0:
            eta_seconds = int(remaining / rate)
```

#### 3.3.4 Score Rounding
```python
avg_score = round(avg_score, 2) if avg_score else None
p90_score = round(p90_score, 2) if p90_score else None
```

## 4. Data Model

### 4.1 Pydantic Schema
**MatchingSummaryResponse** (`models/matching_schemas.py`)
```python
class MatchingSummaryResponse(BaseModel):
    job_id: str
    status: str = Field(..., description="Status: pending | running | completed | failed")
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
```

### 4.2 Field Descriptions
- **job_id**: UUID of the job
- **status**: Current matching status (pending/running/completed/failed)
- **started_at**: Job creation timestamp
- **completed_at**: Job completion timestamp (null if not completed)
- **last_event_at**: Last job update timestamp (proxy for event activity)
- **candidates_total**: Total product-frame pairs to process
- **candidates_processed**: Estimated pairs processed so far
- **vector_pass_total**: Same as candidates_total (for frontend compatibility)
- **vector_pass_done**: Same as candidates_processed (for frontend compatibility)
- **ransac_checked**: Number of matches found (proxy for geometric verification)
- **matches_found**: Total matches in database
- **matches_with_evidence**: Matches with evidence_path populated
- **avg_score**: Average match score (rounded to 2 decimals)
- **p90_score**: 90th percentile match score (rounded to 2 decimals)
- **queue_depth**: RabbitMQ queue depth (placeholder, always 0)
- **eta_seconds**: Estimated time to completion in seconds
- **blockers**: List of blocking issues (placeholder, always empty)

## 5. Router Configuration

### 5.1 Endpoint Registration
**matching_endpoints.py** (`api/matching_endpoints.py`)
```python
router = APIRouter(tags=["matching"])

@router.get(
    "/jobs/{job_id}/matching/summary",
    response_model=MatchingSummaryResponse
)
async def get_matching_summary(
    job_id: str,
    force_refresh: bool = Query(False),
    db=Depends(get_db)
):
    service = MatchingService(db)
    summary = await service.get_matching_summary(job_id, force_refresh)
    
    if not summary:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return summary
```

### 5.2 Router Inclusion
The router must be included in the main FastAPI app:
```python
from api.matching_endpoints import router as matching_router
app.include_router(matching_router)
```

## 6. Error Handling

### 6.1 Service Layer
```python
try:
    # Query and calculation logic
    return MatchingSummaryResponse(...)
except Exception as e:
    logger.error(f"Error getting matching summary for job {job_id}: {e}")
    raise
```

### 6.2 Endpoint Layer
- Returns 404 if job not found
- Propagates exceptions as 500 errors
- Logs all errors for debugging

## 7. Performance Considerations

### 7.1 Query Optimization
- All queries use indexed columns (job_id, product_id, video_id)
- COUNT queries are efficient for current data volumes
- PERCENTILE_CONT may be slow for large match sets (consider caching)

### 7.2 Caching Strategy (Future)
- Consider caching completed job summaries
- Invalidate cache on new match events
- Use `force_refresh` to bypass cache

### 7.3 Database Load
- Frontend polls every 4 seconds during matching
- Multiple concurrent jobs could increase load
- Consider read replicas for high traffic

## 8. Testing Strategy

### 8.1 Unit Tests
```python
# Test status determination
def test_status_mapping():
    assert get_status('matching') == 'running'
    assert get_status('evidence') == 'completed'
    assert get_status('failed') == 'failed'

# Test candidates calculation
def test_candidates_total():
    assert calculate_candidates(10, 20) == 200

# Test ETA calculation
def test_eta_calculation():
    eta = calculate_eta(100, 50, 60)  # total, processed, elapsed
    assert eta == 60  # 50% done in 60s = 60s remaining
```

### 8.2 Integration Tests
```python
# Test full endpoint flow
async def test_matching_summary_endpoint():
    # Create job with products and videos
    # Create some matches
    response = await client.get(f"/jobs/{job_id}/matching/summary")
    assert response.status_code == 200
    assert response.json()["matches_found"] > 0

# Test 404 for missing job
async def test_missing_job():
    response = await client.get("/jobs/invalid-id/matching/summary")
    assert response.status_code == 404
```

### 8.3 Load Tests
- Simulate multiple concurrent requests
- Test with large match sets (1000+ matches)
- Verify query performance under load

## 9. Monitoring and Observability

### 9.1 Logging
```python
logger = configure_logging("main-api:matching_service")
logger.error(f"Error getting matching summary for job {job_id}: {e}")
```

### 9.2 Metrics (Future)
- Request count and latency
- Error rate by status code
- Query execution time
- Cache hit rate (if caching implemented)

### 9.3 Alerts (Future)
- High error rate (>5%)
- Slow queries (>1s)
- Stalled jobs (no updates in >5 minutes)

## 10. Known Limitations

### 10.1 Current Constraints
- **candidates_processed**: Estimated, not actual count
- **queue_depth**: Always 0 (no RabbitMQ integration)
- **blockers**: Always empty (no health check integration)
- **last_event_at**: Uses job.updated_at, not actual event timestamp

### 10.2 Accuracy Issues
- ETA calculation is rough approximation
- Progress may not be linear (depends on match density)
- No distinction between vector search and RANSAC phases

## 11. Future Enhancements

### 11.1 Event Tracking
- Store `match.request` and `matchings.process.completed` events
- Track actual candidates processed from matcher worker
- Use event timestamps for accurate `last_event_at`

### 11.2 Queue Integration
- Query RabbitMQ for actual queue depth
- Detect stalled queues (no consumers)
- Report queue lag in `blockers`

### 11.3 Health Checks
- Integrate with matcher worker health endpoint
- Detect worker crashes or OOM errors
- Report in `blockers` array

### 11.4 Caching
- Cache completed job summaries in Redis
- Invalidate on new match events
- Reduce database load for historical jobs

### 11.5 Real-time Updates
- WebSocket endpoint for streaming updates
- Push notifications on phase transitions
- Eliminate polling overhead

## 12. Migration Notes

### 12.1 Database Changes
No schema changes required. Uses existing tables:
- `jobs`
- `matches`
- `products`
- `product_images`
- `job_videos`
- `video_frames`

### 12.2 Deployment
1. Deploy service code with new endpoint
2. No database migrations needed
3. Frontend can start using immediately
4. Backward compatible (no breaking changes)

## 13. API Documentation

### 13.1 OpenAPI/Swagger
Endpoint automatically documented via FastAPI:
- Path: `/docs#/matching/get_matching_summary_jobs__job_id__matching_summary_get`
- Interactive testing available
- Schema validation included

### 13.2 Example Request
```bash
curl -X GET "http://localhost:8000/jobs/123e4567-e89b-12d3-a456-426614174000/matching/summary?force_refresh=false"
```

### 13.3 Example Response
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "running",
  "started_at": "2025-11-21T10:00:00Z",
  "completed_at": null,
  "last_event_at": "2025-11-21T10:05:12Z",
  "candidates_total": 180,
  "candidates_processed": 75,
  "vector_pass_total": 180,
  "vector_pass_done": 75,
  "ransac_checked": 18,
  "matches_found": 18,
  "matches_with_evidence": 6,
  "avg_score": 0.64,
  "p90_score": 0.82,
  "queue_depth": 0,
  "eta_seconds": 210,
  "blockers": []
}
```
