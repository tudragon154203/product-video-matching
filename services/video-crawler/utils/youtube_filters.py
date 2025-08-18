from datetime import datetime
from typing import Any
from common_py.logging_config import configure_logging

logger = configure_logging("video-crawler")


def filter_valid_entry(entry: Any, cutoff_date: datetime) -> bool:
    """Filter out None/empty entries"""
    return entry is not None


def filter_upload_date(entry: Any, cutoff_date: datetime) -> bool:
    """Filter by upload date - keep videos uploaded after cutoff date"""
    upload_date_str = entry.get('upload_date')
    if not upload_date_str:
        logger.debug(f"Skipping video {entry.get('id', 'unknown')} - no upload date")
        return False
    
    try:
        upload_date = datetime.strptime(upload_date_str, '%Y%m%d')
        upload_date = upload_date.replace(tzinfo=None)  # Remove timezone info for comparison
        
        # Keep videos uploaded after cutoff date
        if upload_date < cutoff_date:
            logger.debug(f"Skipping video {entry.get('id', 'unknown')} - too old (uploaded: {upload_date_str}, cutoff: {cutoff_date.strftime('%Y%m%d')})")
            return False
            
        return True
        
    except ValueError:
        # If we can't parse the date, skip this video
        logger.debug(f"Skipping video {entry.get('id', 'unknown')} - invalid date format: {upload_date_str}")
        return False


def filter_duration(entry: Any, cutoff_date: datetime) -> bool:
    """Filter by duration - keep videos with valid duration"""
    duration = entry.get('duration')
    if duration is None:
        logger.debug(f"Skipping video {entry.get('id', 'unknown')} - no duration")
        return False
    return True