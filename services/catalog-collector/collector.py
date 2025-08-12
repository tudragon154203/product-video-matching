import os
import asyncio
import httpx
from pathlib import Path
from typing import List, Dict, Any, Optional
import structlog
from PIL import Image

logger = structlog.get_logger()


class ProductCollector:
    """Collects products from Amazon and eBay (mock implementation for MVP)"""
    
    def __init__(self, data_root: str):
        self.data_root = Path(data_root)
        self.products_dir = self.data_root / "products"
        self.products_dir.mkdir(parents=True, exist_ok=True)
        
        # HTTP client for downloading images
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
    
    async def collect_amazon_products(self, industry: str, top_k: int) -> List[Dict[str, Any]]:
        """
        Collect Amazon products (mock implementation)
        In production, this would use Amazon Product API
        """
        logger.info("Collecting Amazon products", industry=industry, count=top_k)
        
        # Mock product data for MVP
        mock_products = []
        for i in range(min(top_k, 5)):  # Limit to 5 for testing
            product = {
                "id": f"amazon_{industry}_{i}",
                "title": f"Mock {industry} Product {i+1}",
                "brand": f"Brand{i+1}",
                "url": f"https://amazon.com/mock-product-{i}",
                "images": [
                    f"https://picsum.photos/400/400?random={i*10+j}" 
                    for j in range(3)  # 3 images per product
                ]
            }
            mock_products.append(product)
        
        logger.info("Collected Amazon products", count=len(mock_products))
        return mock_products
    
    async def collect_ebay_products(self, industry: str, top_k: int) -> List[Dict[str, Any]]:
        """
        Collect eBay products (mock implementation)
        In production, this would use eBay API
        """
        logger.info("Collecting eBay products", industry=industry, count=top_k)
        
        # Mock product data for MVP
        mock_products = []
        for i in range(min(top_k, 5)):  # Limit to 5 for testing
            product = {
                "id": f"ebay_{industry}_{i}",
                "title": f"Mock eBay {industry} Item {i+1}",
                "brand": f"EBrand{i+1}",
                "url": f"https://ebay.com/mock-item-{i}",
                "images": [
                    f"https://picsum.photos/400/400?random={i*20+j+100}" 
                    for j in range(2)  # 2 images per product
                ]
            }
            mock_products.append(product)
        
        logger.info("Collected eBay products", count=len(mock_products))
        return mock_products
    
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
            from io import BytesIO
            image = Image.open(BytesIO(response.content))
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize to standard size (keeping aspect ratio)
            image.thumbnail((512, 512), Image.Resampling.LANCZOS)
            
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