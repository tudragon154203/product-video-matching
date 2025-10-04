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