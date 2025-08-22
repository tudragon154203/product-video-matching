import asyncio
import time
from typing import Dict, Any, Optional
from common_py.logging_config import configure_logging
from config_loader import config

logger = configure_logging("dropship-product-finder")

# Fixed filter string from Sprint 1 requirements
FILTER = (
    "buyingOptions:{FIXED_PRICE},"
    "returnsAccepted:true,"
    "deliveryCountry:US,"
    "maxDeliveryCost:0,"
    "price:[10..40],"
    "priceCurrency:USD,"
    "conditionIds:{1000}"
)


class EbayBrowseApiClient:
    """eBay Browse API client with retry logic and authentication"""
    
    def __init__(self, auth_service, marketplace_id: str, base_url: str, httpx_client: Optional[Any] = None):
        self.auth_service = auth_service
        self.marketplace_id = marketplace_id
        self.base_url = base_url.rstrip("/")
        self.httpx_client = httpx_client
        
    async def _make_request_with_retry(self, url: str, headers: dict, params: dict) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        last_error = None
        
        for attempt in range(config.MAX_RETRIES_BROWSE):
            try:
                import httpx
                client = None
                if self.httpx_client:
                    client = self.httpx_client
                else:
                    client = httpx.AsyncClient(timeout=config.TIMEOUT_SECS_BROWSE)

                response = await client.get(url, headers=headers, params=params)

                if not self.httpx_client:
                    await client.aclose() # Close client if it was created within this method

                if response.status_code == 200:
                    try:
                        return response.json()
                    except Exception as e:
                        logger.error(f"Failed to parse response JSON: {e}")
                        return {"itemSummaries": []}
                elif response.status_code == 401:
                    # Token expired, refresh and retry once
                    logger.warning("401 Unauthorized, refreshing token")
                    await self.auth_service.refresh_token()
                    headers["Authorization"] = f"Bearer {await self.auth_service.get_token()}"
                    if attempt == 0:  # Only retry once for 401
                        continue
                    else:
                        logger.error("Still unauthorized after token refresh")
                        return {"itemSummaries": []}
                elif response.status_code in [429, 500, 502, 503, 504]:
                    # Rate limiting or server errors
                    wait_time = config.BACKOFF_BASE_BROWSE ** attempt
                    logger.warning(f"Retry {attempt + 1}/{config.MAX_RETRIES_BROWSE} waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"HTTP {response.status_code}: {response.text}")
                    return {"itemSummaries": []}
                        
            except Exception as e:
                last_error = e
                logger.error(f"Network error during request: {e}") # Added this line
                if attempt < config.MAX_RETRIES_BROWSE - 1:
                    wait_time = config.BACKOFF_BASE_BROWSE ** attempt
                    logger.warning(f"Network error, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                continue
        
        logger.error(f"All retries exhausted: {last_error}")
        return {"itemSummaries": []}
    
    async def search(self, q: str, limit: int, offset: int = 0,
                     extra_filter: Optional[str] = None) -> Dict[str, Any]:
        """Perform keyword search with fixed Sprint-1 filters and EXTENDED fieldgroups."""
        
        # Get fresh token
        token = await self.auth_service.get_access_token()
        
        # Build URL
        search_url = f"{self.base_url}/item_summary/search"
        
        # Build query parameters
        params = {
            "q": q[:100],  # eBay max 100 chars
            "filter": FILTER,
            "fieldgroups": "EXTENDED",
            "limit": min(limit, 50),  # eBay max 50 per page
            "offset": offset
        }
        
        # Add extra filter if provided
        if extra_filter:
            params["filter"] = f"{params['filter']},{extra_filter}"
        
        # Build headers
        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": self.marketplace_id,
            "Content-Type": "application/json"
        }
        
        logger.info(f"eBay search", 
                   marketplace=self.marketplace_id, 
                   query=q, 
                   limit=limit,
                   offset=offset)
        
        # Make request
        start_time = time.time()
        result = await self._make_request_with_retry(search_url, headers, params)
        
        latency = time.time() - start_time
        logger.info("eBay search completed", 
                   marketplace=self.marketplace_id,
                   latency=latency,
                   results_count=len(result.get("itemSummaries", [])),
                   query=q)
        
        return result
    
    async def get_item(self, item_id: str, fieldgroups: str = "ITEM") -> Dict[str, Any]:
        """Get detailed item information including additional images"""
        
        # Get fresh token
        token = await self.auth_service.get_access_token()
        
        # Build URL
        item_url = f"{self.base_url}/item/{item_id}"
        
        # Build query parameters
        params = {
            "fieldgroups": fieldgroups
        }
        
        # Build headers
        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": self.marketplace_id,
            "Content-Type": "application/json"
        }
        
        logger.info(f"eBay get item", 
                   marketplace=self.marketplace_id, 
                   item_id=item_id,
                   fieldgroups=fieldgroups)
        
        # Make request
        start_time = time.time()
        result = await self._make_request_with_retry(item_url, headers, params)
        
        latency = time.time() - start_time
        logger.info("eBay get item completed", 
                   marketplace=self.marketplace_id,
                   latency=latency,
                   item_id=item_id)
        
        return result