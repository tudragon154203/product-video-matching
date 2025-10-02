# Quickstart: TikTok Video Download & Keyframe Extraction

## Prerequisites
- Docker and Docker Compose installed
- Python 3.10.8 with pip (as per constitution)
- Access to the TikTok URLs to be processed
- Video-crawler service running with TikTok capabilities

## Test TikTok Video Links
- Test Video 1: https://www.tiktok.com/@lanxinx/video/7548644205690670337
- Test Video 2: https://www.tiktok.com/@username/video/1234567890
- Test Video 3: https://www.tiktok.com/@creator/video/987654321

## Setup
1. Clone the repository
2. Navigate to the project root directory
3. Run the development environment: `./up-dev.ps1`
4. Run database migrations: `./migrate.ps1`
5. Verify TikTok crawler is configured:
   - Check `TIKTOK_CRAWL_HOST_PORT` environment variable (default: 5680)
   - Ensure TikTok Search API is available at `http://localhost:5680/tiktok/search`

## Configuration
### Environment Variables
```bash
# TikTok crawler configuration
export TIKTOK_CRAWL_HOST_PORT=5680
export TIKTOK_VIDEO_STORAGE_PATH=/data/videos/tiktok
export TIKTOK_KEYFRAME_STORAGE_PATH=/data/keyframes/tiktok

# Video cleanup configuration (optional)
export CLEANUP_OLD_VIDEOS=true
export VIDEO_RETENTION_DAYS=7
```

### TikTok Downloader Configuration
The TikTok downloader includes advanced features:
- **Anti-bot Protection**: Automatic detection and handling of TikTok anti-bot measures
- **Exponential Backoff**: Intelligent retry mechanism with increasing delays
- **File Size Validation**: Enforces 500MB limit and removes oversized files
- **Comprehensive Error Handling**: Handles network timeouts, connection errors, and permission issues

## Running the TikTok Video Downloader

### Method 1: Through Video Crawler Service
1. Start the video-crawler service
2. Submit TikTok search request via the API:
```json
{
  "job_id": "tiktok-test-123",
  "industry": "fashion",
  "queries": {"vi": ["thời trang", "outfit"]},
  "platforms": ["tiktok"],
  "recency_days": 30
}
```

### Method 2: Direct TikTok Download
```python
from platform_crawler.tiktok.tiktok_downloader import TikTokDownloader
import asyncio

async def download_tiktok_video():
    config = {
        'TIKTOK_VIDEO_STORAGE_PATH': '/data/videos/tiktok',
        'TIKTOK_KEYFRAME_STORAGE_PATH': '/data/keyframes/tiktok',
        'retries': 3,
        'timeout': 30
    }
    
    downloader = TikTokDownloader(config)
    
    success = await downloader.orchestrate_download_and_extract(
        url="https://www.tiktok.com/@lanxinx/video/7548644205690670337",
        video_id="test-video-123"
    )
    
    if success:
        print("Download and extraction completed successfully!")
    else:
        print("Download failed")

# Run the download
asyncio.run(download_tiktok_video())
```

## Testing the Feature

### Unit Tests
```bash
# Navigate to video-crawler service
cd services/video-crawler

# Run TikTok-specific unit tests
python -m pytest tests/unit/tiktok/ -v

# Run all unit tests
python -m pytest -m unit -v
```

### Integration Tests
```bash
# Run TikTok integration tests
python -m pytest tests/integration/tiktok/ -v

# Run all integration tests
python -m pytest -m integration -v
```

### Manual Testing
1. Submit a TikTok URL to the crawler
2. Verify the video was downloaded to the configured storage path
3. Check that keyframes were extracted and stored
4. Confirm metadata was saved to the database

## Validation Steps

### File System Validation
- **Video File**: Exists in `TIKTOK_VIDEO_STORAGE_PATH/{video_id}.mp4`
- **Keyframes**: Directory exists in `TIKTOK_KEYFRAME_STORAGE_PATH/{video_id}/`
- **Keyframe Images**: Multiple `.jpg` files in the keyframes directory
- **File Sizes**: Video file < 500MB, keyframe files reasonable size

### Database Validation
```sql
-- Check video record
SELECT video_id, platform, url, title, duration_s, has_download, local_path
FROM videos
WHERE platform = 'tiktok' AND video_id = 'your-video-id';

-- Check keyframe records
SELECT frame_id, video_id, ts, local_path
FROM video_frames
WHERE video_id = 'your-video-id';
```

### Expected Results
- ✅ Video downloaded successfully (file exists and is valid)
- ✅ Keyframes extracted (multiple frame images created)
- ✅ Database records created (video and video_frames entries)
- ✅ No anti-bot errors in logs
- ✅ File size within limits (< 500MB)

## Troubleshooting

### Common Issues
1. **Anti-bot Detection**: Check logs for "Anti-bot measure detected" messages
2. **File Size Errors**: Verify video is under 500MB
3. **Network Timeouts**: Increase timeout in configuration
4. **Permission Issues**: Ensure storage directories are writable

### Log Analysis
```bash
# View TikTok downloader logs
docker compose -f infra/pvm/docker-compose.dev.yml logs -f video-crawler | grep -i tiktok

# Check for errors
docker compose -f infra/pvm/docker-compose.dev.yml logs video-crawler | grep -i error
```

## Cleanup
The system automatically cleans up videos older than 7 days when `CLEANUP_OLD_VIDEOS=true`:
- Videos in `TIKTOK_VIDEO_STORAGE_PATH` older than 7 days are removed
- Keyframes are preserved for processed videos
- Cleanup runs automatically after video processing