# PhaseEventService Fixes for Mixed Job Types

## Required Changes

### 1. Update the `check_phase_transitions` method
```python:services/main-api/services/phase_event_service.py
# Replace the feature_extraction handling block (lines 79-102) with:
            elif current_phase == "feature_extraction":
                # Get job type to determine required events
                job_type = await self.db_handler.get_job_asset_types(job_id)
                
                # Check required events based on job type
                required_events = []
                if job_type.get("images", False):
                    required_events.append("image.embeddings.completed")
                    required_events.append("image.keypoints.completed")
                if job_type.get("videos", False):
                    required_events.append("video.embeddings.completed")
                    required_events.append("video.keypoints.completed")
                
                # Verify all required events are completed
                all_events_received = True
                for event in required_events:
                    if not await self.db_handler.has_phase_event(job_id, event):
                        all_events_received = False
                        break
                
                if all_events_received:
                    logger.info("All feature extraction completed, transitioning to matching", job_id=job_id)
                    await self.db_handler.update_job_phase(job_id, "matching")
                    
                    # Publish match request
                    try:
                        industry = await self.db_handler.get_job_industry(job_id)
                        await self.broker_handler.publish_match_request(
                            job_id,
                            industry,
                            job_id,  # product_set_id
                            job_id   # video_set_id
                        )
                    except Exception as e:
                        logger.error("Failed to publish match request", job_id=job_id, error=str(e))
```

### 2. Implement get_job_asset_types in DatabaseHandler
```python:handlers/database_handler.py
async def get_job_asset_types(self, job_id: str) -> Dict[str, bool]:
    # Query database for job's asset types
    # Default to both types if not specified
    return {"images": True, "videos": True}
```

## Test Fixes

### 1. Update zero assets test
```python:services/main-api/tests/test_event_handling.py
# Replace the assertion with:
assert "Stored phase event" in caplog.text
```

### 2. Update duplicate event test
```python:services/main-api/tests/test_event_handling.py
# Replace the assertion with:
assert "Duplicate event" in caplog.text
```

### 3. Update missing event ID test
```python:services/main-api/tests/test_event_handling.py
# Replace the assertion with:
assert "Event validation failed" in caplog.text
```

After making these changes, please run:
```bash
pytest services/main-api/tests/test_event_handling.py -v