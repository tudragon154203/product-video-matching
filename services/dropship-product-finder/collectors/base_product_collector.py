from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
import httpx
from PIL import Image
from io import BytesIO
from common_py.logging_config import configure_logging
from .interface import IProductCollector

logger = configure_logging("dropship-product-finder")


class BaseProductCollector(IProductCollector):
    """Abstract base class for product collectors"""
    
    def __init__(self, data_root: str):
        self.data_root = Path(data_root)
        self.products_dir = self.data_root / "products"
        self.products_dir.mkdir(parents=True, exist_ok=True)
        
        # HTTP client for downloading images
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
    
    @abstractmethod
    async def collect_products(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Collect products for a given query"""
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Return the source name (e.g., 'amazon', 'ebay')"""
        pass
    
    async def download_image(self, image_url: str, product_id: str, image_id: str) -> Optional[str]:
        """Download and normalize an image"""
        try:
            # Create product directory
            product_dir = self.products_dir / product_id
            product_dir.mkdir(exist_ok=True)
            
            # Download image
            response = await self.client.get(image_url)
            response.raise_for_status()
            
            # Save original image
            image_path = product_dir / f"{image_id}.jpg"
            
            # Process and normalize image
            image = Image.open(BytesIO(response.content))
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize to standard size (keeping aspect ratio)
            image.thumbnail((400, 400), Image.Resampling.LANCZOS)
            
            # Save processed image
            image.save(image_path, "JPEG", quality=90)
            
            logger.info("Downloaded and processed image", 
                       image_id=image_id, path=str(image_path))
            
            return str(image_path)
            
        except Exception as e:
            logger.error("Failed to download image", 
                        image_url=image_url, image_id=image_id, error=str(e))
            return None
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
