from typing import List, Dict, Any, Optional
from collections import defaultdict
from common_py.logging_config import configure_logging

logger = configure_logging("dropship-product-finder:ebay_product_mapper")


class EbayProductMapper:
    """Maps structured data from the ebay_product_parser to the final Product data model."""

    def __init__(self):
        pass

    def normalize_ebay_item(
        self, item: Dict[str, Any], marketplace: str
    ) -> Optional[Dict[str, Any]]:
        """Normalize a single eBay item to internal product shape"""
        try:
            # Extract EPID (optional eBay Product ID)
            epid = item.get("epid")

            # Extract images from all known eBay fields. Real API responses sometimes
            # use `primaryImage`/`additionalImages` instead of the older
            # `image`/`galleryInfo` structure, so we gather from every variant and
            # deduplicate while preserving order.
            images: List[str] = []
            seen: set[str] = set()

            def add_image(url: Optional[str]) -> None:
                if not url or not isinstance(url, str):
                    return
                cleaned = url.strip()
                if not cleaned or cleaned in seen:
                    return
                seen.add(cleaned)
                images.append(cleaned)

            def extract_from_value(value: Any) -> None:
                if isinstance(value, dict):
                    add_image(
                        value.get("imageUrl")
                        or value.get("imageURL")
                        or value.get("url")
                    )
                elif isinstance(value, list):
                    for entry in value:
                        extract_from_value(entry)
                elif isinstance(value, str):
                    add_image(value)

            # Primary image candidates
            extract_from_value(item.get("image"))
            extract_from_value(item.get("primaryImage"))

            # Search summary sometimes exposes direct URLs
            extract_from_value(item.get("imageUrl"))
            extract_from_value(item.get("itemImageUrl"))

            # Collect additional image sources
            gallery_images = (
                item.get("galleryInfo", {}) or {}
            ).get("imageVariations", [])
            extract_from_value(gallery_images)
            extract_from_value(item.get("additionalImages"))
            extract_from_value(item.get("images"))
            extract_from_value(item.get("thumbnailImages"))

            # Limit to maximum of six images (primary + up to five additional)
            images = images[:6]

            if not images:
                logger.warning(
                    "Skipping eBay item with no resolvable images",
                    item_id=item.get("itemId"),
                    marketplace=marketplace,
                )
                return None

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

    def deduplicate_products(
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
