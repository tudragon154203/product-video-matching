from abc import abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
import httpx
from io import BytesIO

try:  # Pillow is optional in unit test environments
    from PIL import Image
except ImportError:  # pragma: no cover - exercised only when Pillow missing
    Image = None
from common_py.logging_config import configure_logging
from .interface import IProductCollector
from config_loader import config

logger = configure_logging("dropship-product-finder:base_product_collector")


class BaseProductCollector(IProductCollector):
    """Abstract base class for product collectors"""

    def __init__(self, data_root: str):
        self.data_root = Path(data_root)
        self.products_dir = self.data_root / "products"
        self.products_dir.mkdir(parents=True, exist_ok=True)

        # HTTP client for downloading images (timeout is configurable)
        self.client = httpx.AsyncClient(
            timeout=config.IMAGE_DOWNLOAD_TIMEOUT_SECS,
            follow_redirects=True
        )

    @abstractmethod
    async def collect_products(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Collect products for a given query"""
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Return the source name (e.g., 'amazon', 'ebay')"""
        pass

    async def download_image(
        self, image_url: str, product_id: str, image_id: str
    ) -> Optional[str]:
        """Download and normalize an image"""
        try:
            # Create product directory
            product_dir = self.products_dir / product_id
            product_dir.mkdir(parents=True, exist_ok=True)

            # Download image
            response = await self.client.get(image_url)
            response.raise_for_status()

            # Save original image
            image_path = product_dir / f"{image_id}.jpg"

            if Image is None:
                image_path.write_bytes(response.content)
                logger.warning(
                    "Saved image without Pillow post-processing",
                    image_id=image_id,
                    path=str(image_path),
                )
            else:
                # Process and normalize image
                image = Image.open(BytesIO(response.content))

                # Convert to RGB if needed
                if image.mode != "RGB":
                    image = image.convert("RGB")

                # Resize to standard size (keeping aspect ratio)
                image.thumbnail((400, 400), Image.Resampling.LANCZOS)

                # Save processed image
                image.save(image_path, "JPEG", quality=90)

            logger.info(
                "Downloaded and processed image",
                image_id=image_id,
                path=str(image_path),
            )

            return str(image_path)

        except Exception as e:
            logger.error(
                "Failed to download image",
                image_url=image_url,
                image_id=image_id,
                error=str(e),
            )
            return None

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
