# Sprint 11: Flexible Language Queries for videos_search_request

## 1) Problem Statement

The `videos_search_request` event schema previously required both `vi` (Vietnamese) and `zh` (Chinese) language queries to always be present, even when only one platform was selected. This caused validation failures when:

- A user selected only YouTube (which uses `vi` queries) → `zh` field was missing
- A user selected only Bilibili (which uses `zh` queries) → `vi` field was missing
- The LLM failed to generate queries for both languages

This rigid requirement forced artificial data generation and didn't reflect the actual platform-language mapping:
- **YouTube, TikTok**: Use Vietnamese (`vi`) queries
- **Bilibili, Douyin**: Use Chinese (`zh`) queries

## 2) Goals

1. **Make language queries flexible**: Allow `videos_search_request` to contain only the languages needed for the selected platforms
2. **Maintain data integrity**: Ensure at least one language is always present
3. **Backward compatibility**: Existing events with both languages continue to work
4. **Graceful degradation**: Services handle missing languages without crashing

## 3) Solution Design

### Schema Changes

**File**: `libs/contracts/contracts/schemas/videos_search_request.json`

**Before**:
```json
"queries": {
  "type": "object",
  "required": ["vi", "zh"],
  "properties": {
    "vi": { "type": "array", "items": {"type": "string"} },
    "zh": { "type": "array", "items": {"type": "string"} }
  }
}
```

**After**:
```json
"queries": {
  "type": "object",
  "minProperties": 1,
  "properties": {
    "vi": { "type": "array", "items": {"type": "string"} },
    "zh": { "type": "array", "items": {"type": "string"} }
  },
  "additionalProperties": true
}
```

**Key changes**:
- Removed `"required": ["vi", "zh"]`
- Added `"minProperties": 1` to ensure at least one language is present
- Both `vi` and `zh` are now optional individually

### Main-API Changes

**File**: `services/main-api/services/llm/prompt_service.py`

Updated `route_video_queries()` to:
1. Map platforms to their primary languages
2. Include only relevant languages based on platform selection
3. Provide fallback logic to ensure at least one language is present

```python
def route_video_queries(self, queries: Dict[str, Any], platforms: list) -> Dict[str, list]:
    """Route video queries based on platforms, ensuring at least one language is present."""
    video_queries = {}
    
    # Map platforms to their primary languages
    vi_platforms = {"youtube", "tiktok"}
    zh_platforms = {"bilibili", "douyin"}
    
    platforms_lower = {p.lower() for p in platforms}
    
    # Add vi queries if relevant platforms are selected
    if vi_platforms & platforms_lower and "vi" in queries.get("video", {}):
        video_queries["vi"] = queries["video"]["vi"]
    
    # Add zh queries if relevant platforms are selected
    if zh_platforms & platforms_lower and "zh" in queries.get("video", {}):
        video_queries["zh"] = queries["video"]["zh"]
    
    # Ensure at least one language is present (fallback)
    if not video_queries:
        if "vi" in queries.get("video", {}):
            video_queries["vi"] = queries["video"]["vi"]
        if "zh" in queries.get("video", {}):
            video_queries["zh"] = queries["video"]["zh"]
    
    return video_queries
```

### Video-Crawler Changes

**File**: `services/video-crawler/services/platform_query_processor.py`

Enhanced `_process_dict_queries()` to handle missing languages gracefully:

```python
@staticmethod
def _process_dict_queries(queries: Dict[str, Any], platforms: List[str]) -> List[str]:
    """Process dictionary-based queries with platform-specific logic."""
    platforms_lower = {platform.lower() for platform in platforms}

    # Prioritize visual content queries for TikTok and YouTube
    if {"tiktok", "youtube"} & platforms_lower:
        prioritized = PlatformQueryProcessor._normalize_to_list(queries.get("vi"))
        if prioritized:
            return prioritized
        # Fallback to zh if vi is not available
        fallback = PlatformQueryProcessor._normalize_to_list(queries.get("zh"))
        if fallback:
            return fallback
        return []

    # For Bilibili, prioritize zh queries
    if "bilibili" in platforms_lower:
        prioritized = PlatformQueryProcessor._normalize_to_list(queries.get("zh"))
        if prioritized:
            return prioritized
        # Fallback to vi if zh is not available
        fallback = PlatformQueryProcessor._normalize_to_list(queries.get("vi"))
        if fallback:
            return fallback
        return []

    # Aggregate queries from all available languages
    aggregated: List[str] = []
    for value in queries.values():
        aggregated.extend(PlatformQueryProcessor._normalize_to_list(value))

    return PlatformQueryProcessor._dedupe_preserve_order(aggregated)
```

## 4) Testing Strategy

### Contract Tests

**File**: `services/main-api/tests/contract/events/test_videos_search_request_contract.py`

Updated existing test:
```python
async def test_videos_search_request_queries_structure():
    """Test that queries field has the correct structure with at least one language."""
    schema = validator.get_schema("videos_search_request")
    queries_schema = schema["properties"]["queries"]
    
    assert queries_schema.get("minProperties") == 1
    assert "vi" not in queries_schema.get("required", [])
    assert "zh" not in queries_schema.get("required", [])
```

Added new test:
```python
async def test_videos_search_request_single_language():
    """Test that videos_search_request works with only one language."""
    
    # Test with only vi
    event_vi_only = {
        "job_id": "test-job-vi",
        "industry": "electronics",
        "queries": {"vi": ["chuột không dây"]},
        "platforms": ["youtube"],
        "recency_days": 30
    }
    assert validator.validate_event("videos_search_request", event_vi_only)
    
    # Test with only zh
    event_zh_only = {
        "job_id": "test-job-zh",
        "industry": "electronics",
        "queries": {"zh": ["无线鼠标"]},
        "platforms": ["bilibili"],
        "recency_days": 30
    }
    assert validator.validate_event("videos_search_request", event_zh_only)
    
    # Test with empty queries (should fail)
    event_empty = {
        "job_id": "test-job-empty",
        "industry": "electronics",
        "queries": {},
        "platforms": ["youtube"],
        "recency_days": 30
    }
    with pytest.raises(Exception):
        validator.validate_event("videos_search_request", event_empty)
```

### Integration Tests

**File**: `services/main-api/tests/integration/events/test_published_event_contracts.py`

Created new integration tests that validate actual published events:

1. `test_youtube_only_publishes_valid_event()`: Verifies YouTube-only jobs publish valid events with only `vi`
2. `test_bilibili_only_publishes_valid_event()`: Verifies Bilibili-only jobs publish valid events with only `zh`
3. `test_mixed_platforms_publishes_valid_event()`: Verifies multi-platform jobs include both languages

### Test Event Validator

**File**: `tests/support/publisher/event_publisher.py`

Updated `EventValidator.validate_videos_search_request()`:
```python
@staticmethod
def validate_videos_search_request(event_data: Dict[str, Any]) -> bool:
    queries = event_data["queries"]
    
    # Ensure at least one language is present
    if len(queries) == 0:
        return False
    
    # If vi or zh are present, they should be non-empty lists
    for lang in ["vi", "zh"]:
        if lang in queries:
            if not isinstance(queries[lang], list) or len(queries[lang]) == 0:
                return False
    
    return True
```

## 5) Documentation Updates

Updated the following documentation files:

1. **AGENTS.md**: Added note about optional languages and platform-language mapping
2. **CONTRACTS.md**: Added detailed notes about `minProperties: 1` and fallback logic
3. **services/video-crawler/README.md**: Updated event example and added platform-language mapping explanation

## 6) Acceptance Criteria

- [x] Schema allows events with only `vi` or only `zh`
- [x] Schema rejects events with empty `queries` object
- [x] Main-API publishes valid events for single-platform jobs
- [x] Video-crawler handles missing languages gracefully with fallback
- [x] Contract tests validate new schema requirements
- [x] Integration tests verify actual published events
- [x] Documentation reflects new flexible behavior
- [x] Backward compatible: existing events with both languages still work

## 7) Migration Notes

**Backward Compatibility**: This change is fully backward compatible. Existing events that include both `vi` and `zh` will continue to validate and process correctly.

**Forward Compatibility**: New events can now include only the languages needed for the selected platforms, reducing unnecessary data and preventing validation failures.

**No Database Changes**: This is purely a schema and validation change. No database migrations are required.

## 8) Example Event Payloads

### YouTube Only
```json
{
  "job_id": "job-123",
  "industry": "electronics",
  "queries": {
    "vi": ["chuột không dây", "đánh giá chuột gaming"]
  },
  "platforms": ["youtube"],
  "recency_days": 30
}
```

### Bilibili Only
```json
{
  "job_id": "job-456",
  "industry": "electronics",
  "queries": {
    "zh": ["无线鼠标", "游戏鼠标评测"]
  },
  "platforms": ["bilibili"],
  "recency_days": 30
}
```

### Mixed Platforms
```json
{
  "job_id": "job-789",
  "industry": "electronics",
  "queries": {
    "vi": ["chuột không dây"],
    "zh": ["无线鼠标"]
  },
  "platforms": ["youtube", "bilibili"],
  "recency_days": 30
}
```

## 9) Implementation Checklist

- [x] Update `videos_search_request.json` schema
- [x] Update `prompt_service.py` route_video_queries()
- [x] Update `platform_query_processor.py` with fallback logic
- [x] Update contract test for queries structure
- [x] Add contract test for single language scenarios
- [x] Create integration tests for published events
- [x] Update test event validator
- [x] Update AGENTS.md documentation
- [x] Update CONTRACTS.md documentation
- [x] Update video-crawler README.md
- [x] Create sprint documentation

## 10) Related Files

### Schema
- `libs/contracts/contracts/schemas/videos_search_request.json`

### Main-API
- `services/main-api/services/llm/prompt_service.py`
- `services/main-api/tests/contract/events/test_videos_search_request_contract.py`
- `services/main-api/tests/integration/events/test_published_event_contracts.py`

### Video-Crawler
- `services/video-crawler/services/platform_query_processor.py`
- `services/video-crawler/README.md`

### Test Support
- `tests/support/publisher/event_publisher.py`

### Documentation
- `AGENTS.md`
- `CONTRACTS.md`
