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
- TikTok: Search videos using TikTok Search API at http://localhost:5680/tiktok/search

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

## In/Out Events
### Input Events
- `videos.search.request`: Request to initiate video search across platforms.
  - Data: `{"job_id": "job-123", "industry": "ergonomic pillows", "queries": {"vi": ["query1", "query2"]}, "platforms": ["youtube", "tiktok"], "recency_days": 30}`
  
  - Data: `{"video_id": "vid-789", "video_url": "http://youtube.com/watch?v=example"}`

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