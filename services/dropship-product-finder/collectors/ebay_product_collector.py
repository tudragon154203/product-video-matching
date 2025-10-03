from typing import List, Dict, Any, Optional
from collections import defaultdict
from .base_product_collector import BaseProductCollector
from services.ebay_browse_api_client import EbayBrowseApiClient
from services.auth import eBayAuthService
from config_loader import config
from common_py.logging_config import configure_logging

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

        # Initialize auth service internally
        self.auth_service = eBayAuthService(config, redis_client)
        self.marketplaces = marketplaces or config.EBAY_MARKETPLACES.split(",")
        self.base_url = config.EBAY_BROWSE_BASE
        self.httpx_client = httpx_client

        # Initialize browse clients for each marketplace
        self.browse_clients = {}
        self._initialize_browse_clients()

    def _initialize_browse_clients(self):
        """Initialize eBayBrowseAPIClient instances for each marketplace"""
        try:
            for marketplace in self.marketplaces:
                marketplace = marketplace.strip()  # Remove any whitespace
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
            # Re-raise the exception to prevent partial initialization
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

        # Close all browse clients
        for marketplace, client in self.browse_clients.items():
            try:
                # Note: Browse clients don't have explicit close methods in current
                # implementation but we should clean up any resources if they do in
                # the future
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

        # Request from each marketplace using pre-initialized clients
        for marketplace in self.marketplaces:
            try:
                # Get the pre-initialized client for this marketplace
                if marketplace not in self.browse_clients:
                    logger.warning(
                        f"No browse client found for marketplace: {marketplace}"
                    )
                    continue

                browse_client = self.browse_clients[marketplace]

                # First, search for items
                search_results = await browse_client.search(
                    q=query, limit=top_k, offset=0
                )

                # Then get detailed item information for additional images
                item_details = []
                for item_summary in search_results.get("itemSummaries", [])[:top_k]:
                    item_id = item_summary["itemId"]
                    try:
                        detailed_item = await browse_client.get_item(
                            item_id, fieldgroups="ITEM"
                        )
                        item_details.append(detailed_item)
                    except Exception as e:
                        logger.warning(f"Failed to get details for item {item_id}: {e}")
                        # Use summary as fallback
                        item_details.append({"item": item_summary})

                # Map results with detailed item information
                marketplace_products = self._map_ebay_results_with_details(
                    search_results.get("itemSummaries", []), item_details, marketplace
                )

                all_products.extend(marketplace_products)

                logger.info(
                    f"Collected {len(marketplace_products)} products from {marketplace}"
                )

            except Exception as e:
                logger.error(f"Failed to collect from {marketplace}", error=str(e))
                continue

        # Deduplicate by EPID and select lowest total price
        deduplicated_products = self._deduplicate_products(all_products, top_k)

        logger.info(
            f"Final eBay products after deduplication: {len(deduplicated_products)}"
        )

        # Check if we got enough results
        if len(deduplicated_products) < top_k:
            logger.warning(
                f"Only {len(deduplicated_products)} products found, requested {top_k}"
            )

        return deduplicated_products

    def _map_ebay_results(
        self, items: List[Dict[str, Any]], marketplace: str
    ) -> List[Dict[str, Any]]:
        """Map eBay API responses to internal product shape"""
        products = []

        for item in items:
            product = self._normalize_ebay_item(item, marketplace)
            if product:
                products.append(product)

        return products

    def _map_ebay_results_with_details(
        self,
        summaries: List[Dict[str, Any]],
        item_details: List[Dict[str, Any]],
        marketplace: str,
    ) -> List[Dict[str, Any]]:
        """Map eBay search results with detailed item information"""
        products = []

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

            product = self._normalize_ebay_item(item_data, marketplace)
            if product:
                products.append(product)

        return products

    def _normalize_ebay_item(
        self, item: Dict[str, Any], marketplace: str
    ) -> Optional[Dict[str, Any]]:
        """Normalize a single eBay item to internal product shape"""
        try:
            # Extract EPID (optional eBay Product ID)
            epid = item.get("epid")

            # Extract images - handle both search response and detailed item response
            images = []

            # Try to get image from different possible sources
            primary_image = None

            # Option 1: From detailed item response
            if "image" in item and isinstance(item["image"], dict):
                primary_image = item["image"].get("imageUrl")

            # Option 2: From item gallery images (in detailed response)
            if not primary_image and "galleryInfo" in item:
                gallery_images = item["galleryInfo"].get("imageVariations", [])
                if gallery_images:
                    primary_image = gallery_images[0].get("imageUrl")

            # Option 3: From search response fallback
            if not primary_image:
                primary_image = item.get("image", {}).get("imageUrl")

            if primary_image:
                images.append(primary_image)

            # Extract additional images from multiple possible sources
            additional_images = []

            # Option 1: From detailed item gallery images
            if "galleryInfo" in item:
                gallery_images = item["galleryInfo"].get("imageVariations", [])
                for img in gallery_images[1:]:  # Skip first (already added as primary)
                    if img.get("imageUrl"):
                        additional_images.append(img["imageUrl"])

            # Option 2: From item.images array (if available in detailed response)
            if (
                not additional_images
                and "images" in item
                and isinstance(item["images"], list)
            ):
                for img in item["images"][1:]:  # Skip first
                    if img.get("imageUrl"):
                        additional_images.append(img["imageUrl"])

            # Limit additional images to 5 total
            additional_count = min(5, 6 - len(images))
            additional_images = additional_images[:additional_count]
            images.extend(additional_images)

            # Extract shipping cost from EXTENDED fieldgroup
            shipping_cost = 0
            if item.get("shippingOptions"):
                for option in item["shippingOptions"]:
                    if option.get("shippingType") == "FREE":
                        shipping_cost = 0
                        break
                    elif option.get("cost"):
                        shipping_cost = option["cost"]["value"]
                        break

            # Calculate total price (price + shipping)
            price_value = float(item.get("price", {}).get("value", 0))
            shipping_cost = float(
                item.get("shippingOptions", [{}])[0]
                .get("shippingCost", {})
                .get("value", 0)
            )
            total_price = price_value + shipping_cost

            product = {
                "id": epid or item["itemId"],
                "title": item.get("title", ""),
                "brand": item.get("brand") or item.get("manufacturer"),
                "url": item.get("itemWebUrl") or item.get("itemAffiliateWebUrl"),
                "images": images,
                "marketplace": marketplace.lower().replace("ebay_", ""),
                "price": price_value,
                "currency": item.get("price", {}).get("currency", "USD"),
                "epid": epid,
                "itemId": item["itemId"],
                "totalPrice": total_price,
                "shippingCost": shipping_cost,
            }

            return product

        except Exception as e:
            logger.error("Failed to normalize eBay item", error=str(e), item=item)
            return None

    def _deduplicate_products(
        self, products: List[Dict[str, Any]], max_items: int
    ) -> List[Dict[str, Any]]:
        """Deduplicate by EPID and select lowest total price"""
        if not products:
            return []

        # Group by EPID, fallback to itemId
        grouped = defaultdict(list)
        for product in products:
            key = product.get("epid") or product.get("itemId")
            grouped[key].append(product)

        # Select lowest total from each group
        deduplicated = []
        for key, group in grouped.items():
            # Sort by total price and select lowest
            selected = min(group, key=lambda p: p["totalPrice"])
            deduplicated.append(selected)

        # Sort by total price and limit
        deduplicated.sort(key=lambda p: p["totalPrice"])
        return deduplicated[:max_items]
