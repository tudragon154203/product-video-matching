# Event Testing Remaining Tasks

## Code Changes Needed
1. Update `check_phase_transitions` in `PhaseEventService` to handle single-media-type jobs:
   ```python:services/phase_event_service.py
   job_type = await self.db_handler.get_job_asset_types(job_id)
   required_events = []
   if job_type.get("images", False):
       required_events.append("image.embeddings.completed")
       required_events.append("image.keypoints.completed")
   if job_type.get("videos", False):
       required_events.append("video.embeddings.completed")
       required_events.append("video.keypoints.completed")
   ```

2. Implement `get_job_asset_types` in DatabaseHandler:
   ```python:handlers/database_handler.py
   async def get_job_asset_types(self, job_id: str) -> Dict[str, bool]:
       # Query database for job's asset types
       return {"images": True, "videos": True}  # Default to both
   ```

## Test Adjustments
1. Update zero assets test to check standard log message:
   ```python:services/main-api/tests/test_event_handling.py
   assert f"Stored phase event for job {job_id}" in caplog.text
   ```

2. Update timeout test to check partial completion message:
   ```python:services/main-api/tests/test_event_handling.py
   assert "Job completed with partial results" in caplog.text
   ```

3. Update missing event ID test:
   ```python:services/main-api/tests/test_event_handling.py
   assert "Event validation failed" in caplog.text
   assert "'event_id' is a required property" in caplog.text
   ```

## Recommended Next Steps
1. Implement the DatabaseHandler's get_job_asset_types method
2. Update PhaseEventService to handle job-specific events
3. Adjust test assertions to match actual log formats
4. Re-run the full test suite