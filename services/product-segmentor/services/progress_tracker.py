"""Tracks progress of image and frame processing for jobs."""

from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class JobProgress:
    """Progress tracking for a single job asset type."""
    total: int = 0
    processed: int = 0


class ProgressTracker:
    """Tracks job progress for images and frames."""
    
    def __init__(self):
        self._job_progress: Dict[str, Dict[str, JobProgress]] = {}
        # Structure: {job_id: {'image': JobProgress, 'frame': JobProgress}}
    
    def init(self, job_id: str, total: int, kind: str) -> None:
        """Initialize progress for a job asset type.
        
        Args:
            job_id: Job identifier
            total: Total number of assets to process
            kind: 'image' or 'frame'
        """
        if job_id not in self._job_progress:
            self._job_progress[job_id] = {}
        
        self._job_progress[job_id][kind] = JobProgress(total=total, processed=0)
    
    def inc(self, job_id: str, kind: str) -> None:
        """Increment processed count for a job asset type.
        
        Args:
            job_id: Job identifier
            kind: 'image' or 'frame'
        """
        if job_id in self._job_progress and kind in self._job_progress[job_id]:
            self._job_progress[job_id][kind].processed += 1
    
    def get(self, job_id: str, kind: str) -> Optional[JobProgress]:
        """Get progress for a job asset type.
        
        Args:
            job_id: Job identifier
            kind: 'image' or 'frame'
            
        Returns:
            JobProgress or None if not found
        """
        if job_id in self._job_progress:
            return self._job_progress[job_id].get(kind)
        return None
    
    def get_job_counts(self, job_id: str) -> Dict[str, Dict[str, int]]:
        """Get all progress counts for a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Dict with structure: {'image': {'total': int, 'processed': int}, 'frame': {...}}
        """
        if job_id not in self._job_progress:
            return {'image': {'total': 0, 'processed': 0}, 'frame': {'total': 0, 'processed': 0}}
        
        result = {}
        for kind, progress in self._job_progress[job_id].items():
            result[kind] = {'total': progress.total, 'processed': progress.processed}
        return result
    
    def clear(self, job_id: str) -> None:
        """Clear progress tracking for a job.
        
        Args:
            job_id: Job identifier
        """
        if job_id in self._job_progress:
            del self._job_progress[job_id]
    
    def get_all_job_counts(self) -> Dict[str, Dict[str, Dict[str, int]]]:
        """Get all job progress counts for backward compatibility.
        
        Returns:
            Dict with structure matching original job_image_counts and job_frame_counts
        """
        result = {}
        for job_id, kinds in self._job_progress.items():
            job_counts = {}
            for kind, progress in kinds.items():
                job_counts[kind] = {'total': progress.total, 'processed': progress.processed}
            result[job_id] = job_counts
        return result
    
    def update_job_counts(self, job_id: str, kind: str, total: int, processed: int) -> None:
        """Update job counts for a specific asset type.
        
        Args:
            job_id: Job identifier
            kind: 'image' or 'frame'
            total: Total number of assets
            processed: Number of processed assets
        """
        if job_id not in self._job_progress:
            self._job_progress[job_id] = {}
        
        if kind not in self._job_progress[job_id]:
            self._job_progress[job_id][kind] = JobProgress()
        
        self._job_progress[job_id][kind].total = total
        self._job_progress[job_id][kind].processed = processed
    
    def increment_processed(self, job_id: str, kind: str) -> None:
        """Increment processed count for a job asset type.
        
        Args:
            job_id: Job identifier
            kind: 'image' or 'frame'
        """
        if job_id in self._job_progress and kind in self._job_progress[job_id]:
            self._job_progress[job_id][kind].processed += 1
    
    def remove_job(self, job_id: str) -> None:
        """Remove a job from tracking.
        
        Args:
            job_id: Job identifier
        """
        if job_id in self._job_progress:
            del self._job_progress[job_id]
    
    def clear_all(self) -> None:
        """Clear all job progress tracking."""
        self._job_progress.clear()
    
    def get_job_progress(self, job_id: str, type_name: str) -> 'JobProgress':
        """Get job progress information.
        
        Args:
            job_id: Job identifier
            type_name: Type ('image' or 'frame')
            
        Returns:
            JobProgress object with progress information
        """
        if job_id not in self._job_progress:
            return JobProgress(total=0, processed=0)
        
        progress = self._job_progress[job_id].get(type_name)
        if progress is None:
            return JobProgress(total=0, processed=0)
        
        return progress