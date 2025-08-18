from typing import List, Callable, Any, Tuple
from datetime import datetime
from common_py.logging_config import configure_logging

logger = configure_logging("video-crawler")


class FilterChain:
    """
    A chain of filters that can be applied to a list of items.
    
    This class allows for flexible filtering of data by applying multiple
    filter functions in sequence, with support for tracking skipped items.
    """
    
    def __init__(self):
        """Initialize an empty filter chain."""
        self.filters: List[Callable[[Any, datetime], bool]] = []
    
    def add_filter(self, filter_func: Callable[[Any, datetime], bool]) -> None:
        """
        Add a filter function to the chain.
        
        Args:
            filter_func: A function that takes an item and cutoff_date,
                        returns a boolean indicating whether to keep the item
        """
        self.filters.append(filter_func)
    
    def apply(self, items: List[Any], cutoff_date: datetime) -> Tuple[List[Any], int]:
        """
        Apply all filters in the chain to a list of items.
        
        Args:
            items: List of items to filter
            cutoff_date: Cutoff date for recency filtering
            
        Returns:
            Tuple of (filtered_items, skipped_count)
        """
        if not self.filters:
            return items, 0
        
        filtered_items = []
        skipped_count = 0
        
        for item in items:
            should_keep = True
            skip_reason = ""
            
            # Apply all filters
            for filter_func in self.filters:
                if not filter_func(item, cutoff_date):
                    should_keep = False
                    break
            
            if should_keep:
                filtered_items.append(item)
            else:
                skipped_count += 1
                # Log the skip reason at debug level
                logger.debug(f"Skipping item {getattr(item, 'id', 'unknown')} - {skip_reason}")
        
        return filtered_items, skipped_count