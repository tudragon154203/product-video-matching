"""
Utility functions for video-related operations.
"""
from typing import Optional, Dict, Any

from common_py.logging_config import configure_logging
from common_py.crud.video_frame_crud import VideoFrameCRUD
from utils.image_utils import to_public_url

logger = configure_logging("main-api:video_utils")


async def select_preview_frame(
    video_id: str,
    duration_s: float,
    video_frame_crud: VideoFrameCRUD,
    data_root: str
) -> Optional[Dict[str, Any]]:
    """
    Select the best preview frame for a video based on the selection rules.

    Selection rules (best-effort, deterministic):
    1) Prefer a frame with has_segment == true and valid local_path for the segment.
    2) Else pick a frame with valid raw image path.
    3) Prefer middle timestamp (~duration/2); break ties by newest updated_at then lowest frame_id.
    4) If no frames or invalid paths, return None.

    Args:
        video_id: The video ID to get frames for
        duration_s: The duration of the video in seconds
        video_frame_crud: VideoFrameCRUD instance
        data_root: The data root path for URL derivation

    Returns:
        Dict with frame_id, ts, url, segment_url or None if no suitable frame found
    """
    try:
        # Get all frames for the video
        frames = await video_frame_crud.list_video_frames_by_video(
            video_id=video_id,
            limit=1000,  # Get all frames, assuming reasonable number
            offset=0,
            sort_by="ts",
            order="ASC"
        )

        if not frames:
            logger.debug(f"No frames found for video {video_id}")
            return None

        # Filter frames with valid paths
        valid_frames = []
        for frame in frames:
            # Check if raw frame path is valid
            raw_url = to_public_url(frame.local_path, data_root)
            if raw_url:
                frame_data = {
                    'frame': frame,
                    'raw_url': raw_url,
                    'segment_url': None,
                    'has_segment': False,
                    'priority': 2  # Lower priority for raw frames
                }

                # Check if segmented frame exists and is valid
                if hasattr(frame, 'segment_local_path') and frame.segment_local_path:
                    segment_url = to_public_url(
                        frame.segment_local_path, data_root)
                    if segment_url:
                        frame_data['segment_url'] = segment_url
                        frame_data['has_segment'] = True
                        # Higher priority for segmented frames
                        frame_data['priority'] = 1

                valid_frames.append(frame_data)

        if not valid_frames:
            logger.debug(
                f"No valid frames with paths found for video {video_id}")
            return None

        # Sort frames by priority, then by distance from middle timestamp,
        # then by updated_at (newest first), then by frame_id (lowest first)
        target_ts = duration_s / 2

        def sort_key(frame_data):
            frame = frame_data['frame']
            distance_from_middle = abs(frame.ts - target_ts)
            # Use negative updated_at for descending order (newest first)
            updated_at_val = getattr(frame, 'updated_at', None)
            return (
                # Priority first (segmented frames preferred)
                frame_data['priority'],
                distance_from_middle,    # Closest to middle timestamp
                # Newest first, None sorts last
                -(updated_at_val.timestamp() if updated_at_val else float('-inf')),
                frame.frame_id           # Lowest frame_id as tiebreaker
            )

        valid_frames.sort(key=sort_key)

        # Select the best frame
        best_frame_data = valid_frames[0]
        best_frame = best_frame_data['frame']

        return {
            'frame_id': best_frame.frame_id,
            'ts': best_frame.ts,
            'url': best_frame_data['raw_url'],
            'segment_url': best_frame_data['segment_url']
        }

    except Exception as e:
        logger.warning(
            f"Error selecting preview frame for video {video_id}: {e}")
        return None


async def get_first_keyframe_url(
    video_id: str,
    video_frame_crud: VideoFrameCRUD,
    data_root: str
) -> Optional[str]:
    """
    Get the public URL of the first keyframe (lowest timestamp) for a video.

    Args:
        video_id: The video ID to get the first keyframe for
        video_frame_crud: VideoFrameCRUD instance
        data_root: The data root path for URL derivation

    Returns:
        Public URL of the first keyframe or None if not found or invalid
    """
    try:
        # Get frames sorted by ts ascending, limit to 1 to get the first one
        frames = await video_frame_crud.list_video_frames_by_video(
            video_id=video_id,
            limit=1,
            offset=0,
            sort_by="ts",
            order="ASC"
        )

        if not frames:
            logger.debug(f"No frames found for video {video_id}")
            return None

        first_frame = frames[0]

        # Convert local_path to public URL
        public_url = to_public_url(first_frame.local_path, data_root)
        if public_url:
            # Prefix with MAIN_API_URL if needed, but since to_public_url returns relative, and in endpoints it's prefixed
            # Actually, looking at video_endpoints.py line 220: public_url = f"{config.MAIN_API_URL}{public_url}"
            # But for consistency with preview_frame, which has url as the full relative path, wait no:
            # In select_preview_frame, it returns 'url': raw_url, which is the relative path from to_public_url
            # Then in endpoints, it's used directly: url=preview_frame_data['url']
            # But in FrameItem, url is prefixed: public_url = f"{config.MAIN_API_URL}{public_url}"
            # Inconsistency? For frames endpoint, it's prefixed, but for preview_frame in videos, it's not.
            # Looking at PreviewFrame schema: url: str, and in video_endpoints it's set to preview_frame_data['url'] which is relative.
            # Probably the frontend prefixes it.
            # To match, I'll return the relative URL like select_preview_frame does.
            return public_url
        else:
            logger.debug(
                f"Could not generate public URL for first frame of video {video_id}")
            return None

    except Exception as e:
        logger.warning(
            f"Error getting first keyframe for video {video_id}: {e}")
        return None
