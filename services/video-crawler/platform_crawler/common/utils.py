from __future__ import annotations

from typing import Any, Callable, Dict, Iterable


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
