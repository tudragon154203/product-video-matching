# Research: TikTok Video Download & Keyframe Extraction

## Decision: yt-dlp for TikTok video downloading
**Rationale:** yt-dlp is the recommended successor to youtube-dl and has robust support for various video platforms including TikTok. It handles anti-bot measures and different content restrictions better than alternatives.
**Alternatives considered:** 
- youtube-dl (deprecated, no longer maintained)
- Custom TikTok API scraping (would require significant maintenance as TikTok changes their API)
- TikTok Scraper libraries (limited and less reliable than yt-dlp)

## Decision: Reuse existing keyframe extraction module
**Rationale:** The existing length_adaptive_extractor.py module is already proven for YouTube videos, and extending it to handle TikTok videos reduces development time and ensures consistency.
**Alternatives considered:**
- Using a different keyframe extraction library (would introduce additional dependencies)
- Building a custom keyframe extractor (unnecessary complexity when existing solution works)

## Decision: Python version for development
**Rationale:** Following the constitution mandate to use Python 3.10.8 for consistency across all services in the system.
**Alternatives considered:**
- Using the latest Python version (would create inconsistency with other services)
- Using Python 3.11 (would violate the constitution)

## Decision: File storage approach for temporary files
**Rationale:** Following the existing pattern in the codebase with temporary storage locations for videos and keyframes, with automatic cleanup after 7 days as specified in the requirements.
**Alternatives considered:**
- Cloud storage (more complex setup, adds dependencies on external services)
- In-memory processing (not feasible for large video files)

## Decision: Error handling and retry mechanisms
**Rationale:** Implementing retries with exponential backoff for network failures ensures resilience, while specific handling for TikTok's anti-bot measures allows the system to continue processing other videos when individual downloads fail.
**Alternatives considered:**
- No retries (would result in more failed downloads)
- Infinite retries (could cause system to hang on permanently unavailable content)

## Decision: Video and keyframe storage location
**Rationale:** Following the same approach as the YouTube implementation by storing videos in DATA_ROOT_CONTAINER/videos/ and keyframes in DATA_ROOT_CONTAINER/keyframes/ as defined in the system configuration, rather than in temporary directories which are only for unit testing.
**Alternatives considered:**
- Storing in temp directory (only appropriate for unit testing, not production)
- Storing in custom location (would create inconsistency with YouTube implementation)

## Configuration Implementation
**Details:** Based on the system configuration, videos are stored in `os.path.join(config.DATA_ROOT_CONTAINER, "videos")` (default `/app/data/videos`) and keyframes in `os.path.join(config.DATA_ROOT_CONTAINER, "keyframes")` (default `/app/data/keyframes`).

## Decision: No RabbitMQ event contracts for this feature
**Rationale:** After reviewing requirements, it was determined that no new RabbitMQ event contracts are needed for this TikTok video download feature.
**Alternatives considered:**
- Creating new event contracts (not required per updated requirements)
- Extending existing contracts (not necessary for this feature scope)

## Test TikTok Video
**Test Link:** https://www.tiktok.com/@lanxinx/video/7548644205690670337
**Purpose:** This video will be used for testing the download and keyframe extraction functionality.