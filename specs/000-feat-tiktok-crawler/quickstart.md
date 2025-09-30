# Quickstart: TikTok Platform Crawler

## Overview
This guide helps you quickly test and verify the TikTok crawler integration. The TikTok crawler connects to an external TikTok Search API at `http://localhost:5680/tiktok/search` to search for videos and retrieve metadata.

## Prerequisites
- TikTok Search API running on `http://localhost:5680`
- Video Crawler service running and connected to RabbitMQ
- Database accessible with proper schema

## Quick Test Steps

### 1. Test TikTok API Directly
```bash
# Test the TikTok Search API endpoint
curl -X POST http://localhost:5680/tiktok/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "ergonomic pillows",
    "numVideos": 5,
    "force_headful": false
  }'
```

**Expected Response**:
```json
{
  "results": [
    {
      "id": "video_123456789",
      "caption": "Check out this amazing ergonomic pillow!",
      "authorHandle": "@comfortlover",
      "likeCount": 12345,
      "uploadTime": "2024-01-01T12:00:00Z",
      "webViewUrl": "https://www.tiktok.com/@comfortlover/video/123456789"
    }
  ],
  "totalResults": 150,
  "query": "ergonomic pillows",
  "search_metadata": {
    "executed_path": "/tiktok/search",
    "execution_time": 450,
    "request_hash": "abc123def456"
  }
}
```

### 2. Test via Main API
```bash
# Start a job with TikTok platform
curl -X POST http://localhost:8000/start-job \
  -H "Content-Type: application/json" \
  -d '{
    "industry": "ergonomic pillows",
    "top_amz": 10,
    "top_ebay": 5,
    "platforms": ["tiktok"],
    "recency_days": 365
  }'
```

### 3. Verify RabbitMQ Events
Check RabbitMQ management UI (`http://localhost:15672`) for existing events:
- `videos.search.request` (with platform "tiktok")
- `videos.collections.completed` (includes TikTok results)
- `videos.keyframes.ready` (for individual TikTok videos)

### 4. Check Database Results
```sql
-- Check videos table for TikTok results
SELECT * FROM videos WHERE platform = 'tiktok';

-- Check video metadata for TikTok-specific fields
SELECT vm.*
FROM video_metadata vm
JOIN videos v ON vm.video_id = v.video_id
WHERE v.platform = 'tiktok';
```

### 5. Verify Results API
```bash
# Get matching results
curl "http://localhost:8080/results?min_score=0.8&platform=tiktok"
```

## Error Scenarios to Test

### API Unavailable
1. Stop the TikTok Search API
2. Start a job with TikTok platform
3. Verify retry logic works (3 attempts, 15s intervals)
4. Check standard error handling within existing event flow

### Invalid Requests
```bash
# Test with empty query
curl -X POST http://localhost:5680/tiktok/search \
  -H "Content-Type: application/json" \
  -d '{"query": ""}'

# Test with too many videos
curl -X POST http://localhost:5680/tiktok/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "numVideos": 100}'
```

## Performance Testing

### Concurrent Requests
```bash
# Test with 10 concurrent requests
for i in {1..10}; do
  curl -X POST http://localhost:5680/tiktok/search \
    -H "Content-Type: application/json" \
    -d '{"query": "test $i", "numVideos": 5}' &
done
wait
```

### Streaming Verification
Verify that results stream in real-time rather than waiting for batch completion.

## Integration Checklist

- [ ] TikTok API responds to direct requests
- [ ] Existing RabbitMQ events work with platform="tiktok"
- [ ] Videos are stored in database with platform="tiktok"
- [ ] TikTok metadata is preserved in video_metadata
- [ ] Error handling works for API failures within existing event flow
- [ ] Results are accessible via Results API
- [ ] Real-time streaming works as expected
- [ ] Retry logic functions correctly (3 attempts, 15s intervals)
- [ ] Data retention policy enforced (7 days)

## Troubleshooting

### Common Issues
1. **TikTok API not responding**: Check if `http://localhost:5680/tiktok/search` is accessible
2. **Database errors**: Verify PostgreSQL is running and schema exists
3. **RabbitMQ connection issues**: Check RabbitMQ management UI
4. **Rate limiting**: Verify `RATE_LIMIT_REQUESTS_PER_HOUR` configuration

### Logs to Check
- Video Crawler service logs
- TikTok Search API logs
- RabbitMQ event logs
- Database query logs

### Debug Endpoints
```bash
# Health check
curl http://localhost:5680/health

# API status
curl http://localhost:5680/status
```