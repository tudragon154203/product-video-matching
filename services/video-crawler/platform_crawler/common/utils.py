from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List


def deduplicate_by_key(
    videos: Iterable[Dict[str, Any]],
    key: Callable[[Dict[str, Any]], Any] | str,
) -> Dict[Any, Dict[str, Any]]:
    """Return a dictionary of videos keyed by the provided identifier."""
    key_func: Callable[[Dict[str, Any]], Any]
    if callable(key):
        key_func = key
    else:
        key_name = key

        def _key_func(video: Dict[str, Any]) -> Any:
            return video.get(key_name)

        key_func = _key_func

    unique: Dict[Any, Dict[str, Any]] = {}
    for video in videos:
        identifier = key_func(video)
        if identifier and identifier not in unique:
            unique[identifier] = video
    return unique


def deduplicate_videos_by_id_and_title(
    videos: Iterable[Dict[str, Any]],
    id_keys: List[str] | str = "video_id",
    title_key: str = "title"
) -> List[Dict[str, Any]]:
    """
    Deduplicate videos by ID first, then by title for videos with non-null titles.

    This function implements a two-pass deduplication strategy:
    1. First pass: Remove duplicates by video ID (existing behavior)
    2. Second pass: From ID-unique videos, remove duplicates by exact title match,
       keeping only the first occurrence of each title.

    Args:
        videos: Iterable of video dictionaries
        id_keys: Key(s) to use for ID-based deduplication. Can be a single key
                (string) or list of keys to try in order.
        title_key: Key to use for title-based deduplication

    Returns:
        List of deduplicated videos, preserving original order as much as possible
    """
    if isinstance(id_keys, str):
        id_keys = [id_keys]

    # First pass: Deduplicate by ID
    id_unique_videos = {}
    for video in videos:
        video_id = None
        for key in id_keys:
            if key in video and video[key] is not None:
                video_id = video[key]
                break

        # If no ID found, we can't deduplicate by ID, so include the video
        if video_id is None:
            # Use a unique identifier based on the video itself
            video_id = f"no_id_{id(video)}"

        if video_id not in id_unique_videos:
            id_unique_videos[video_id] = video

    # Second pass: Deduplicate by title for videos with non-null titles
    title_unique_videos = []
    seen_titles = set()

    for video_id, video in id_unique_videos.items():
        title = video.get(title_key)

        # If title is None, empty, or already seen, skip this video
        # (unless it was the first occurrence of this title)
        if title is None or title == "":
            title_unique_videos.append(video)
            continue

        # Clean up title for exact matching
        cleaned_title = str(title).strip()

        if cleaned_title not in seen_titles:
            seen_titles.add(cleaned_title)
            title_unique_videos.append(video)
        # If title already seen, skip this video (duplicate by title)

    return title_unique_videos
