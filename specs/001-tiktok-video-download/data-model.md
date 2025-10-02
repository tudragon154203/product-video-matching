# Data Model: TikTok Video Download & Keyframe Extraction

## Test Video
- Test Video: https://www.tiktok.com/@lanxinx/video/7548644205690670337

## Video Entity
**Description:** Represents a TikTok video with download and keyframe extraction status

**Fields:**
- `id: str` - Unique identifier for the video
- `url: str` - Original TikTok URL
- `title: str | None` - Video title (optional)
- `uploader: str | None` - Video uploader (optional)
- `download_url: str | None` - Direct download URL for the video
- `local_path: str | None` - Path to locally stored video file in DATA_ROOT_CONTAINER like YouTube counterpart
- `has_download: bool = False` - Flag indicating if video has been downloaded
- `keyframes: list[str] | None` - List of paths to extracted keyframe images

## Keyframe Entity
**Description:** Represents an extracted keyframe from a video

**Fields:**
- `video_id: str` - Reference to the parent video
- `frame_path: str` - Path to the keyframe image file in DATA_ROOT_CONTAINER like YouTube counterpart
- `timestamp: float` - Time in the video where the frame was extracted (in seconds)
- `keyframe_id: str` - Unique identifier for the keyframe

