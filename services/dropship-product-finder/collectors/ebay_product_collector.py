from typing import List, Dict, Any, Optional
from collections import defaultdict
from .base_product_collector import BaseProductCollector
from services.ebay_browse_api_client import EbayBrowseApiClient
from services.auth import eBayAuthService
from config_loader import config
from common_py.logging_config import configure_logging

logger = configure_logging("dropship-product-finder")


class EbayProductCollector(BaseProductCollector):
    """eBay product collector using real Browse API"""
    
    def __init__(self, data_root: str, auth_service: eBayAuthService,
                 marketplaces: Optional[List[str]] = None):
        super().__init__(data_root, auth_service)
        self.marketplaces = (marketplaces or config.EBAY_MARKETPLACES.split(","))
        self.base_url = config.EBAY_BROWSE_BASE
        
    def get_source_name(self) -> str:
        """Return the source name"""
        return "ebay"
    
    async def collect_products(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Collect products for eBay marketplace with deduplication"""
        logger.info(f"Collecting eBay products", 
                   query=query, 
                   top_k=top_k,
                   marketplaces=self.marketplaces)
        
        all_products = []
        
        # Request from each marketplace
        for marketplace in self.marketplaces:
            try:
                browse_client = EbayBrowseApiClient(
                    auth_service=self.auth_service,
                    marketplace_id=marketplace,
                    base_url=self.base_url
                )
                
                results = await browse_client.search(
                    q=query,
                    limit=top_k,
                    offset=0
                )
                
                marketplace_products = self._map_ebay_results(
                    results.get("itemSummaries", []),
                    marketplace
                )
                
                all_products.extend(marketplace_products)
                
                logger.info(f"Collected {len(marketplace_products)} products from {marketplace}")
                
            except Exception as e:
                logger.error(f"Failed to collect from {marketplace}", error=str(e))
                continue
        
        # Deduplicate by EPID and select lowest total price
        deduplicated_products = self._deduplicate_products(all_products, top_k)
        
        logger.info(f"Final eBay products after deduplication: {len(deduplicated_products)}")
        
        # Check if we got enough results
        if len(deduplicated_products) < top_k:
            logger.warning(f"Only {len(deduplicated_products)} products found, requested {top_k}")
        
        return deduplicated_products
    
    def _map_ebay_results(self, items: List[Dict[str, Any]], marketplace: str) -> List[Dict[str, Any]]:
        """Map eBay API responses to internal product shape"""
        products = []
        
        for item in items:
            product = self._normalize_ebay_item(item, marketplace)
            if product:
                products.append(product)
        
        return products
    
    def _normalize_ebay_item(self, item: Dict[str, Any], marketplace: str) -> Optional[Dict[str, Any]]:
        """Normalize a single eBay item to internal product shape"""
        try:
            # Extract EPID (optional eBay Product ID)
            epid = item.get("epid")
            
            # Extract primary and additional images
            images = []
            primary_image = item.get("image", {}).get("imageUrl")
            if primary_image:
                images.append(primary_image)
            
            # Additional images (up to 6 total)
            additional_images = item.get("additionalImages", [])
            additional_count = min(5, 6 - len(images))  # Max 5 additional
            for img in additional_images[:additional_count]:
                if img.get("imageUrl"):
                    images.append(img["imageUrl"])
            
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
            price_value = item.get("price", {}).get("value", 0)
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
                "shippingCost": shipping_cost
            }
            
            return product
            
        except Exception as e:
            logger.error("Failed to normalize eBay item", error=str(e), item=item)
            return None
    
    def _deduplicate_products(self, products: List[Dict[str, Any]], max_items: int) -> List[Dict[str, Any]]:
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