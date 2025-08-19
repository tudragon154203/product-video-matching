from typing import Optional, List, Dict, Any
from ..database import DatabaseManager
from ..models import ProductImage

class ProductImageCRUD:
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    async def create_product_image(self, image: ProductImage) -> str:
        """Create a new product image"""
        query = """
        INSERT INTO product_images (img_id, product_id, local_path, kp_blob_path, phash)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING img_id
        """
        return await self.db.fetch_val(
            query, image.img_id, image.product_id, image.local_path,
            image.kp_blob_path, image.phash
        )
    
    async def update_embeddings(self, img_id: str, emb_rgb: List[float], emb_gray: List[float]):
        """Update embeddings for a product image"""
        # Convert lists to vector format for PostgreSQL
        rgb_vector = '[' + ','.join(map(str, emb_rgb)) + ']'
        gray_vector = '[' + ','.join(map(str, emb_gray)) + ']'
        
        query = """
        UPDATE product_images 
        SET emb_rgb = $2::vector, emb_gray = $3::vector
        WHERE img_id = $1
        """
        await self.db.execute(query, img_id, rgb_vector, gray_vector)
    
    async def get_product_image(self, img_id: str) -> Optional[ProductImage]:
        """Get a product image by ID"""
        query = "SELECT * FROM product_images WHERE img_id = $1"
        row = await self.db.fetch_one(query, img_id)
        return ProductImage(**row) if row else None
    
    async def list_product_images(self, product_id: str) -> List[ProductImage]:
        """List images for a product"""
        query = "SELECT * FROM product_images WHERE product_id = $1"
        rows = await self.db.fetch_all(query, product_id)
        return [ProductImage(**row) for row in rows]
