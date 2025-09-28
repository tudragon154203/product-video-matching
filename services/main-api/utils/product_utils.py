"""
Utility functions for product-related operations.
"""
from typing import Optional, Tuple

from common_py.logging_config import configure_logging
from common_py.crud.product_image_crud import ProductImageCRUD
from utils.image_utils import to_public_url

logger = configure_logging("main-api:product_utils")


async def select_primary_images(
    product_id: str,
    product_image_crud: ProductImageCRUD,
    data_root: str
) -> Tuple[Optional[str], int]:
    """
    Select the primary image for a product based on selection rules.

    Selection rules (best-effort, deterministic):
    1) Choose the product image most recently updated.
    2) Break ties by lowest img_id.
    3) If no valid images or paths, return (None, 0)

    Args:
        product_id: The product ID to get images for
        product_image_crud: ProductImageCRUD instance
        data_root: The data root path for URL derivation

    Returns:
        Tuple of (primary_image_url, image_count)
    """
    try:
        # Get all images for the product
        images = await product_image_crud.list_product_images(
            product_id=product_id
        )

        image_count = len(images)

        if not images:
            logger.debug(f"No images found for product {product_id}")
            return None, 0

        # Filter images with valid paths
        valid_images = []
        for image in images:
            # Check if original image path is valid
            primary_url = to_public_url(image.local_path, data_root)
            if primary_url:
                valid_images.append({
                    'image': image,
                    'primary_url': primary_url
                })

        if not valid_images:
            logger.debug(
                f"No valid images with paths found for product {product_id}")
            return None, image_count

        # Sort images by: updated_at (newest first), then by img_id (lowest first)
        def sort_key(image_data):
            image = image_data['image']
            # Use negative updated_at for descending order (newest first)
            updated_at_val = getattr(image, 'updated_at', None)
            return (
                # Newest first, None sorts last
                -(updated_at_val.timestamp() if updated_at_val else float('-inf')),
                image.img_id  # Lowest img_id as tiebreaker
            )

        valid_images.sort(key=sort_key)

        # Select the best image
        best_image_data = valid_images[0]

        return (
            best_image_data['primary_url'],
            image_count
        )

    except Exception as e:
        logger.warning(
            f"Error selecting primary images for product {product_id}: {e}")
        return None, 0
