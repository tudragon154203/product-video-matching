from typing import List, Dict, Any, Optional
from collections import defaultdict
from ..base_product_collector import BaseProductCollector
from services.ebay_browse_api_client import EbayBrowseApiClient
from services.auth import eBayAuthService
from config_loader import config
from common_py.logging_config import configure_logging
from .ebay_api_client import EbayApiClient
from .ebay_product_parser import EbayProductParser
from .ebay_product_mapper import EbayProductMapper

logger = configure_logging("dropship-product-finder:ebay_product_collector")


class EbayProductCollector(BaseProductCollector):
    """eBay product collector using real Browse API"""

    def __init__(
        self,
        data_root: str,
        marketplaces: Optional[List[str]] = None,
        httpx_client: Optional[Any] = None,
        redis_client: Optional[Any] = None,
    ):
        super().__init__(data_root)

        self.auth_service = eBayAuthService(config, redis_client)
        self.marketplaces = marketplaces or config.EBAY_MARKETPLACES.split(",")
        self.base_url = config.EBAY_BROWSE_BASE
        self.httpx_client = httpx_client

        self.browse_clients = {}
        self._initialize_browse_clients()

        self.ebay_parser = EbayProductParser()
        self.ebay_mapper = EbayProductMapper()

    def _initialize_browse_clients(self):
        """Initialize eBayBrowseAPIClient instances for each marketplace"""
        try:
            for marketplace in self.marketplaces:
                marketplace = marketplace.strip()
                if marketplace:
                    logger.info(
                        f"Initializing browse client for marketplace: {marketplace}"
                    )
                    self.browse_clients[marketplace] = EbayBrowseApiClient(
                        auth_service=self.auth_service,
                        marketplace_id=marketplace,
                        base_url=self.base_url,
                        httpx_client=self.httpx_client,
                    )
            marketplaces_list = list(self.browse_clients.keys())
            logger.info(
                "Initialized %s browse clients for marketplaces: %s",
                len(self.browse_clients),
                marketplaces_list,
            )
        except Exception as e:
            logger.error(f"Failed to initialize browse clients: {e}")
            raise

    def update_redis_client(self, redis_client: Any) -> None:
        """Update the Redis client for the internal auth service."""
        self.auth_service.update_redis_client(redis_client)

    def get_source_name(self) -> str:
        """Return the source name"""
        return "ebay"

    async def close(self):
        """Close HTTP client and browse clients"""
        await super().close()

        for marketplace, client in self.browse_clients.items():
            try:
                logger.info(f"Closed browse client for marketplace: {marketplace}")
            except Exception as e:
                logger.error(f"Failed to close browse client for {marketplace}: {e}")

        self.browse_clients.clear()

    async def collect_products(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Collect products for eBay marketplace with deduplication"""
        logger.info(
            "Collecting eBay products",
            query=query,
            top_k=top_k,
            marketplaces=self.marketplaces,
        )

        all_products = []

        for marketplace in self.marketplaces:
            try:
                if marketplace not in self.browse_clients:
                    logger.warning(
                        f"No browse client found for marketplace: {marketplace}"
                    )
                    continue

                browse_client = self.browse_clients[marketplace]
                ebay_api_client = EbayApiClient(browse_client)

                summaries, item_details = await ebay_api_client.fetch_and_get_details(
                    query=query, limit=top_k, offset=0, marketplace=marketplace, top_k=top_k
                )

                parsed_items = self.ebay_parser.parse_search_results_with_details(
                    summaries, item_details
                )

                marketplace_products = [
                    self.ebay_mapper.normalize_ebay_item(item, marketplace)
                    for item in parsed_items
                ]
                marketplace_products = [p for p in marketplace_products if p is not None]

                all_products.extend(marketplace_products)

                logger.info(
                    f"Collected {len(marketplace_products)} products from {marketplace}"
                )

            except Exception as e:
                logger.error(f"Failed to collect from {marketplace}", error=str(e))
                continue

        deduplicated_products = self.ebay_mapper.deduplicate_products(all_products, top_k)

        logger.info(
            f"Final eBay products after deduplication: {len(deduplicated_products)}"
        )

        if len(deduplicated_products) < top_k:
            logger.warning(
                f"Only {len(deduplicated_products)} products found, requested {top_k}"
            )

        return deduplicated_products