# Video Crawler Microservice

## Overview
This microservice is responsible for processing video content, including searching for videos across multiple platforms, downloading, segmenting, and extracting frames. It prepares video data for further analysis and matching.

## Functionality
- Searches for videos across multiple platforms (YouTube, TikTok).
- Downloads video content from specified URLs (e.g., YouTube).
- Segments videos into manageable chunks or extracts key frames.
- Publishes video frames for embedding and keypoint extraction.

## Supported Platforms
- YouTube: Search and download videos using yt-dlp
- TikTok: Search videos using TikTok Search API and download videos using configurable strategies (yt-dlp or Scrapling API)

## TikTok Platform Integration
The TikTok crawler connects to an external TikTok Search API to search for videos and retrieve metadata. The crawler features:
- Real-time search with exponential backoff for error handling
- Support for up to 50 videos per search request
- Integration with existing event flow (no new events required)
- 7-day data retention policy

### TikTok Configuration
- Environment variable: `TIKTOK_CRAWL_HOST_PORT=5680` (default)
- API endpoint: `http://localhost:{TIKTOK_CRAWL_HOST_PORT}/tiktok/search`
- Request format: `{"query": "...", "numVideos": 10, "force_headful": false}`

## TikTok Video Download
The TikTok downloader provides robust video download capabilities with configurable strategies:

### Download Strategies

#### 1. Scrapling API Strategy (Default)
- **API-Based Downloads**: Delegates video downloading to external `/tiktok/download` API
- **Automatic Retries**: Built-in headful retry logic for failed downloads
- **Streaming Downloads**: Efficient file streaming to minimize memory usage
- **Metadata Extraction**: Automatic extraction of video metadata from API response

#### 2. yt-dlp Strategy
- **Anti-bot Protection**: Automatic detection and handling of TikTok anti-bot measures
- **Exponential Backoff**: Intelligent retry mechanism with increasing delays (1s, 2s, 4s, etc.)
- **Format Flexibility**: Multiple video format fallbacks for compatibility
- **Direct Download**: Downloads videos directly from TikTok using yt-dlp

#### 3. TikWM Strategy
- **Direct Media Access**: Downloads directly from TikWM's public media endpoint
- **Lightweight**: Minimal dependencies, no external API services required
- **Fast Redirect Resolution**: Uses HEAD requests to resolve final download URLs
- **Retry Logic**: Small retry envelope for transient HTTP failures with backoff

### Common Features
- **File Size Validation**: Enforces 500MB limit and removes oversized files
- **Comprehensive Error Handling**: Handles network timeouts, connection errors, and permission issues
- **Keyframe Extraction**: Automatic extraction of keyframes after successful download
- **Structured Logging**: Detailed logging with strategy identification and metrics

### Download Configuration
- **Download Strategy**: `TIKTOK_DOWNLOAD_STRATEGY` (default: `scrapling-api`, options: `yt-dlp`, `scrapling-api`, `tikwm`)
- **API Host**: `TIKTOK_CRAWL_HOST` (default: `localhost`)
- **API Port**: `TIKTOK_CRAWL_HOST_PORT` (default: `5680`)
- **Download Timeout**: `TIKTOK_DOWNLOAD_TIMEOUT` (default: `180` seconds)
- **Storage Path**: `TIKTOK_VIDEO_STORAGE_PATH` (default: `{DATA_ROOT_CONTAINER}/videos/tiktok`)
- **Keyframe Path**: `TIKTOK_KEYFRAME_STORAGE_PATH` (default: `{DATA_ROOT_CONTAINER}/keyframes/tiktok`)
- **Retry Attempts**: Configurable number of download retries (default: 3)
- **Timeout**: Download timeout in seconds (default: 30)

### Error Handling
- **TikTokAntiBotError**: Custom exception for anti-bot detection
- **Strategy-Specific Errors**: Detailed error codes for API failures
- **Automatic Retries**: Failed downloads automatically retry with appropriate strategy
- **Graceful Degradation**: Database errors don't fail the entire download process
- **Comprehensive Logging**: Detailed logging for debugging and monitoring

### Observability and Metrics
- **Structured Logging**: Strategy identification in all log messages
- **Performance Metrics**: Execution time tracking for both overall and API-specific operations
- **Success Rate Monitoring**: Strategy-specific success/failure tracking
- **Error Classification**: Detailed error code reporting for troubleshooting

### Strategy Selection
```bash
# Use Scrapling API strategy (default)
TIKTOK_DOWNLOAD_STRATEGY=scrapling-api

# Use yt-dlp strategy
TIKTOK_DOWNLOAD_STRATEGY=yt-dlp

# Use TikWM strategy
TIKTOK_DOWNLOAD_STRATEGY=tikwm
```

### Usage Example
```python
from platform_crawler.tiktok.tiktok_downloader import TikTokDownloader

# Initialize downloader
config = {
    'TIKTOK_VIDEO_STORAGE_PATH': '/path/to/videos',
    'TIKTOK_KEYFRAME_STORAGE_PATH': '/path/to/keyframes',
    'retries': 3,
    'timeout': 30
}
downloader = TikTokDownloader(config)

# Orchestrate complete download and extraction
success = await downloader.orchestrate_download_and_extract(
    url="https://www.tiktok.com/@username/video/123456789",
    video_id="unique-video-id",
    video=video_object,  # Optional
    db=database_manager   # Optional
)
```

### File Paths and Naming
- **Videos**: Stored as `{video_id}.mp4` in the video storage directory
- **Keyframes**: Stored in `{video_id}/` subdirectory within the keyframe storage directory
- **Database**: Video metadata and keyframe information persisted to `videos` and `video_frames` tables

## In/Out Events
### Input Events
- `videos.search.request`: Request to initiate video search across platforms.
  - Data: `{"job_id": "job-123", "industry": "ergonomic pillows", "queries": {"vi": ["query1", "query2"], "zh": ["query3"]}, "platforms": ["youtube", "tiktok"], "recency_days": 30}`
  - Note: The `queries` field must contain at least one language (`vi` for Vietnamese or `zh` for Chinese). Both languages are optional but at least one must be present.
  - Platform-language mapping:
    - YouTube, TikTok: Use `vi` (Vietnamese) queries
    - Bilibili, Douyin: Use `zh` (Chinese) queries

### Output Events
- `videos.collections.completed`: Event indicating that video collection has completed across all platforms.
  - Data: `{"job_id": "job-123", "total_videos": 50}`
- `videos.keyframes.ready`: Event containing keyframes extracted from a video.
  - Data: `{"video_id": "vid-789", "keyframes": [{"frame_id": "f1", "ts": 1.0, "local_path": "/path/frame1.jpg"}, ...], "job_id": "job-123"}`
- `VideoProcessed`: Event indicating that a video has been successfully processed.
  - Data: `{"video_id": "vid-789", "total_frames": 1000, "duration": 120.5}`
- `VideoFrameExtracted`: Event containing a single video frame for further processing.
  - Data: `{"video_id": "vid-789", "frame_number": 10, "frame_url": "http://example.com/frame_10.jpg"}`

## Current Progress
- Basic video downloading and frame extraction implemented.
- Integration with video processing libraries.
- Multi-platform support (YouTube and TikTok).
- Real-time streaming response handling for TikTok.

## What's Next
- Implement more efficient video segmentation strategies.
- Add support for various video sources and formats.
- Optimize frame extraction for performance.

## Testing

The video crawler service includes comprehensive unit and integration tests organized by category:

### Test Categories
- `unit`: Fast, isolated unit tests (default)
- `integration`: Integration tests with external dependencies
- `youtube`: YouTube-specific functionality tests
- `real_api`: Tests requiring live API access (skipped by default)
- `slow`: Performance and stress tests

### Running Tests

```bash
# Navigate to service directory first
cd services/video-crawler

# Run only unit tests (fastest, recommended for development)
python -m pytest -m unit

# Run only integration tests
python -m pytest -m integration

# Run only YouTube-specific tests
python -m pytest -m youtube

# Run all tests (includes all categories)
python -m pytest tests/ -v

# Run with coverage
python -m pytest --cov=platform_crawler --cov=keyframe_extractor --cov=services
```

### Test Organization
```
tests/
├── unit/                    # Unit tests (pytest.mark.unit)
│   ├── keyframe_extraction/
│   ├── tiktok/
│   ├── youtube/
│   └── ...
├── integration/            # Integration tests (pytest.mark.integration)
│   ├── youtube/
│   └── ...
└── contract/               # API contract validation
    ├── events/
    └── http/
```