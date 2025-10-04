from typing import List, Dict, Any, Optional
from common_py.logging_config import configure_logging

logger = configure_logging("dropship-product-finder:ebay_product_parser")

class EbayProductParser:
    """Parses raw eBay API responses into a structured format."""

    def __init__(self):
        pass

    def parse_search_results_with_details(
        self,
        summaries: List[Dict[str, Any]],
        item_details: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Parses eBay search results with detailed item information."""
        parsed_items = []
        for i, item_summary in enumerate(summaries):
            if i < len(item_details):
                detailed_item = item_details[i]
                # For detailed response, extract from detailed_item
                if "item" in detailed_item:
                    item_data = detailed_item["item"]
                else:
                    item_data = item_summary
            else:
                item_data = item_summary
            parsed_items.append(item_data)
        return parsed_items

    def parse_search_results(
        self, items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Parses eBay search results."""
        return items