from datetime import datetime
from typing import Any, Tuple
from common_py.logging_config import configure_logging

logger = configure_logging("video-crawler")


def filter_valid_entry(entry: Any, cutoff_date: datetime) -> Tuple[bool, str]:
    """Filter out None/empty entries"""
    if entry is None:
        return False, "Entry is None"
    return True, ""


def filter_duration(entry: Any, cutoff_date: datetime) -> Tuple[bool, str]:
    """Filter by duration - keep videos with valid duration"""
    duration = entry.get('duration')
    if duration is None:
        return False, "No duration"
    return True, ""