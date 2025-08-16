from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
import httpx
from PIL import Image
import structlog
from io import BytesIO

logger = structlog.get_logger()


class BaseProductCollector(ABC):
    """Abstract base class for product collectors"""
    
    def __init__(self, data_root: str, auth_service=None):
        self.data_root = Path(data_root)
        self.products_dir = self.data_root / "products"
        self.products_dir.mkdir(parents=True, exist_ok=True)
        
        # HTTP client for downloading images
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        self.auth_service = auth_service
    
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


class MockProductCollector(BaseProductCollector):
    """Mock product collector for testing"""
    
    async def collect_products(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Collect mock products"""
        source = self.get_source_name()
        logger.info(f"Collecting {source} products", query=query, count=top_k)
        
        # Mock product data for MVP
        mock_products = []
        for i in range(min(top_k, 5)):  # Limit to 5 for testing
            product = {
                "id": f"{source}_{query}_{i}",
                "title": f"Mock {query} Product {i+1}",
                "brand": f"{source.capitalize()}{i+1}",
                "url": f"https://{source}.com/mock-product-{i}",
                "images": [
                    f"https://picsum.photos/400/400?random={i*10+j}"
                    for j in range(1 + (i % 3))  # 1-4 representative images 
                ]
            }
            mock_products.append(product)
        
        logger.info(f"Collected {source} products", count=len(mock_products))
        return mock_products
    
    def get_source_name(self) -> str:
        """Return the source name"""
        return "mock"


class AmazonProductCollector(MockProductCollector):
    """Amazon product collector (currently mock implementation)"""
    
    def get_source_name(self) -> str:
        """Return the source name"""
        return "amazon"


class EbayProductCollector(BaseProductCollector):
    """eBay product collector with OAuth authentication"""
    
    def __init__(self, data_root: str, auth_service=None):
        super().__init__(data_root, auth_service)
        self.base_url = "https://api.ebay.com/buy/browse/v1"
        
    async def collect_products(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Collect products from eBay API"""
        source = self.get_source_name()
        logger.info(f"Collecting {source} products", query=query, count=top_k)
        
        try:
            # Get access token
            if self.auth_service:
                access_token = await self.auth_service.get_access_token()
                headers = {"Authorization": f"Bearer {access_token}"}
            else:
                headers = {}
            
            # Search for products
            search_url = f"{self.base_url}/item_summary/search"
            params = {
                "q": query,
                "limit": min(top_k, 100),  # eBay API limit
                "fieldgroups": "FULL"
            }
            
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(search_url, headers=headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                items = data.get("itemSummaries", [])
                
                # Transform eBay response to our format
                products = []
                for item in items[:top_k]:
                    product = {
                        "id": item.get("itemId"),
                        "title": item.get("title"),
                        "brand": item.get("seller", {}).get("username"),
                        "url": item.get("itemWebUrl"),
                        "images": [img.get("imageUrl") for img in item.get("imageUrls", []) if img.get("imageUrl")]
                    }
                    products.append(product)
                
                logger.info(f"Collected {source} products", count=len(products))
                return products
                
        except httpx.HTTPStatusError as e:
            logger.debug("eBay HTTP error details",
                        status_code=e.response.status_code,
                        url=str(e.request.url) if e.request else "unknown",
                        response_text=e.response.text[:200] if hasattr(e.response, 'text') else "unknown")
            
            if e.response.status_code == 401 and self.auth_service:
                # Check if it's a real token error or a scope/permission issue
                error_response = e.response.json() if hasattr(e.response, 'json') else {}
                error_id = error_response.get('errors', [{}])[0].get('errorId') if error_response.get('errors') else None
                
                if error_id == 1001:  # Invalid access token - might be scope issue
                    logger.error("eBay OAuth scope/permission error",
                               error_id=error_id,
                               response_text=e.response.text[:200])
                    return []
                else:
                    # Token expired, refresh and retry (but only once to avoid infinite loop)
                    logger.info("Token expired, refreshing...")
                    await self.auth_service._refresh_token()
                    return await self.collect_products(query, top_k)
            else:
                logger.error("eBay API error", status_code=e.response.status_code, error=str(e))
                return []
        except Exception as e:
            logger.error("Failed to collect eBay products", error=str(e))
            return []
    
    def get_source_name(self) -> str:
        """Return the source name"""
        return "ebay"
    
    async def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting to avoid hitting eBay API limits"""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug("Rate limiting, sleeping", sleep_time=sleep_time)
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = asyncio.get_event_loop().time()