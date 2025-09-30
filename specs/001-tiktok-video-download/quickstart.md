# Quickstart: TikTok Video Download & Keyframe Extraction

## Prerequisites
- Docker and Docker Compose installed
- Python 3.10.8 with pip (as per constitution)
- Access to the TikTok URLs to be processed

## Test TikTok Video Link
- Test Video: https://www.tiktok.com/@lanxinx/video/7548644205690670337

## Setup
1. Clone the repository
2. Navigate to the project root directory
3. Run the development environment: `./up-dev.ps1`
4. Run database migrations: `./migrate.ps1`

## Running the TikTok Video Downloader
1. Start the video-crawler service with TikTok download capability
2. Submit TikTok webViewUrl to the service
3. The service will:
   - Download the video using yt-dlp to `DATA_ROOT_CONTAINER/videos/tiktok/` like the YouTube counterpart
   - Extract keyframes to `DATA_ROOT_CONTAINER/keyframes/tiktok/{video_id}/` like the YouTube counterpart
   - Store metadata in the database

## Testing the Feature
1. Submit a TikTok URL to the crawler
2. Verify the video was downloaded to the temporary location
3. Check that keyframes were extracted and stored
4. Confirm metadata was saved to the database

## Validation Steps
- Video file exists in `DATA_ROOT_CONTAINER/videos/tiktok/`
- Keyframe images exist in `DATA_ROOT_CONTAINER/keyframes/tiktok/{video_id}/`
- Database contains video record with `has_download=true` and keyframe paths