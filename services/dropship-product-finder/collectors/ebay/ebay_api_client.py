from typing import List, Dict, Any
from services.ebay_browse_api_client import EbayBrowseApiClient
from common_py.logging_config import configure_logging

logger = configure_logging("dropship-product-finder:ebay_api_client")

class EbayApiClient:
    """Encapsulates all interactions with the eBay API."""

    def __init__(self, browse_client: EbayBrowseApiClient):
        self.browse_client = browse_client

    async def fetch_and_get_details(
        self,
        query: str,
        limit: int,
        offset: int,
        marketplace: str,
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """Fetches detailed item information and returns raw results."""
        search_results = await self.browse_client.search(
            q=query, limit=limit, offset=offset
        )

        item_details = []
        for item_summary in search_results.get("itemSummaries", [])[:top_k]:
            item_id = item_summary["itemId"]
            try:
                detailed_item = await self.browse_client.get_item(
                    item_id, fieldgroups="ITEM"
                )
                item_details.append(detailed_item)
            except Exception as e:
                logger.warning(f"Failed to get details for item {item_id}: {e}")
                # Use summary as fallback
                item_details.append({"item": item_summary})
        return search_results.get("itemSummaries", []), item_details