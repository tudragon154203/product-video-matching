from typing import Optional, List, Dict, Any
import uuid
from ..database import DatabaseManager
from ..models import Product

class ProductCRUD:
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    async def create_product(self, product: Product) -> str:
        """Create a new product"""
        query = """
        INSERT INTO products (product_id, src, asin_or_itemid, title, brand, url, marketplace)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING product_id
        """
        return await self.db.fetch_val(
            query, product.product_id, product.src, product.asin_or_itemid,
            product.title, product.brand, product.url, product.marketplace
        )
    
    async def get_product(self, product_id: str) -> Optional[Product]:
        """Get a product by ID"""
        query = "SELECT * FROM products WHERE product_id = $1"
        row = await self.db.fetch_one(query, product_id)
        return Product(**row) if row else None
    
    async def list_products(self, limit: int = 100, offset: int = 0) -> List[Product]:
        """List products with pagination"""
        query = "SELECT * FROM products ORDER BY created_at DESC LIMIT $1 OFFSET $2"
        rows = await self.db.fetch_all(query, limit, offset)
        return [Product(**row) for row in rows]
