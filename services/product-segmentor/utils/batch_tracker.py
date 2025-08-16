"""Batch tracking utilities for product segmentor service."""

from datetime import datetime
from typing import Dict, Optional


class BatchTracker:
    """Tracks batch processing completion."""
    
    def __init__(self, job_id: str, batch_type: str, total_count: int):
        """Initialize batch tracker.
        
        Args:
            job_id: Job identifier
            batch_type: Type of batch ("products" or "keyframes")
            total_count: Total number of items in batch
        """
        self.job_id = job_id
        self.batch_type = batch_type
        self.total_count = total_count
        self.processed_count = 0
        self.created_at = datetime.utcnow()
    
    def increment_processed(self) -> None:
        """Increment processed count."""
        self.processed_count += 1
    
    def is_complete(self) -> bool:
        """Check if batch processing is complete."""
        return self.processed_count >= self.total_count