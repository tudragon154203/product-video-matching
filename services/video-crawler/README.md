# Video Crawler Microservice

## Overview
This microservice is responsible for processing video content, including downloading, segmenting, and extracting frames. It prepares video data for further analysis and matching.

## Functionality
- Downloads video content from specified URLs (e.g., YouTube).
- Segments videos into manageable chunks or extracts key frames.
- Publishes video frames for embedding and keypoint extraction.

## In/Out Events
### Input Events
- `VideoIngestionRequest`: Request to initiate video processing for a given URL.
  - Data: `{"video_id": "vid-789", "video_url": "http://youtube.com/watch?v=example"}`

### Output Events
- `VideoProcessed`: Event indicating that a video has been successfully processed.
  - Data: `{"video_id": "vid-789", "total_frames": 1000, "duration": 120.5}`
- `VideoFrameExtracted`: Event containing a single video frame for further processing.
  - Data: `{"video_id": "vid-789", "frame_number": 10, "frame_url": "http://example.com/frame_10.jpg"}`

## Current Progress
- Basic video downloading and frame extraction implemented.
- Integration with video processing libraries.

## What's Next
- Implement more efficient video segmentation strategies.
- Add support for various video sources and formats.
- Optimize frame extraction for performance.