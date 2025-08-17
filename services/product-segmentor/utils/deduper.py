"""Deduplication service for tracking processed assets."""

from typing import Set


class Deduper:
    """Tracks processed assets to avoid duplicate processing."""
    
    def __init__(self):
        """Initialize the deduper."""
        self._processed_assets: Set[str] = set()
    
    def seen(self, asset_key: str) -> bool:
        """Check if an asset has been processed.
        
        Args:
            asset_key: Unique key for the asset (format: "job_id:asset_id")
            
        Returns:
            True if asset has been processed
        """
        return asset_key in self._processed_assets
    
    def mark(self, asset_key: str) -> None:
        """Mark an asset as processed.
        
        Args:
            asset_key: Unique key for the asset (format: "job_id:asset_id")
        """
        self._processed_assets.add(asset_key)
    
    def clear(self, job_id: str) -> None:
        """Clear all processed assets for a job.
        
        Args:
            job_id: Job identifier
        """
        # Remove all assets belonging to this job
        assets_to_remove = [key for key in self._processed_assets if key.startswith(f"{job_id}:")]
        for asset_key in assets_to_remove:
            self._processed_assets.remove(asset_key)
    
    def clear_all(self) -> None:
        """Clear all processed assets."""
        self._processed_assets.clear()
    
    def get_processed_count(self) -> int:
        """Get the total number of processed assets.
        
        Returns:
            Number of processed assets
        """
        return len(self._processed_assets)
    
    def get_processed_assets(self) -> Set[str]:
        """Get all processed asset keys.
        
        Returns:
            Set of processed asset keys
        """
        return self._processed_assets.copy()
    
    # Backward compatibility aliases
    def is_processed(self, asset_key: str) -> bool:
        """Alias for seen() method for backward compatibility."""
        return self.seen(asset_key)
    
    def mark_processed(self, asset_key: str) -> None:
        """Alias for mark() method for backward compatibility."""
        self.mark(asset_key)