from typing import List, Callable, Any, Tuple
from datetime import datetime
from common_py.logging_config import configure_logging

logger = configure_logging("video-crawler:filter_chain")


class FilterChain:
    """
    A chain of filters that can be applied to a list of items.
    
    This class allows for flexible filtering of data by applying multiple
    filter functions in sequence, with support for tracking skipped items.
    """
    
    def __init__(self):
        """Initialize an empty filter chain."""
        # Store filters as a list of (name, function) tuples
        self.filters: List[Tuple[str, Callable[[Any, datetime], Tuple[bool, str]]]] = []
    
    def add_filter(self, name: str, filter_func: Callable[[Any, datetime], Tuple[bool, str]]) -> None:
        """
        Add a filter function to the chain with a given name.
        
        Args:
            name: A descriptive name for the filter.
            filter_func: A function that takes an item and cutoff_date,
                        returns a tuple of (boolean indicating whether to keep the item, reason string if skipped).
        """
        self.filters.append((name, filter_func))
    
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
            skipped_by_filter = ""
            
            # Apply all filters
            for name, filter_func in self.filters:
                keep, reason = filter_func(item, cutoff_date)
                if not keep:
                    should_keep = False
                    skip_reason = reason
                    skipped_by_filter = name
                    break
            
            if should_keep:
                filtered_items.append(item)
            else:
                skipped_count += 1
                # Log the skip reason at debug level
                item_id = item.get('id', 'unknown') if isinstance(item, dict) else getattr(item, 'id', 'unknown')
                logger.debug(f"Skipping item {item_id} by filter '{skipped_by_filter}': {skip_reason}")
        
        return filtered_items, skipped_count
