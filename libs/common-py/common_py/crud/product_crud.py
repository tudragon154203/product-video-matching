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
    
    async def list_products_by_job(
        self,
        job_id: str,
        search_query: Optional[str] = None,
        src: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "updated_at",
        order: str = "DESC"
    ) -> List[Product]:
        """List products for a job with filtering, search, pagination and sorting."""
        # Validate sort_by parameter
        valid_sort_fields = {"product_id", "title", "brand", "src", "created_at"}
        if sort_by not in valid_sort_fields:
            sort_by = "created_at"
        
        # Validate order parameter
        order = order.upper()
        if order not in {"ASC", "DESC"}:
            order = "DESC"
        
        # Build query with filters
        query = "SELECT * FROM products WHERE job_id = $1"
        params = [job_id]
        param_index = 2
        
        # Add src filter if provided
        if src:
            query += f" AND src = ${param_index}"
            params.append(src)
            param_index += 1
        
        # Add search filter if provided
        if search_query:
            query += f" AND (title ILIKE ${param_index} OR brand ILIKE ${param_index + 1} OR asin_or_itemid ILIKE ${param_index + 2})"
            search_pattern = f"%{search_query}%"
            params.extend([search_pattern, search_pattern, search_pattern])
            param_index += 3
        
        # Add sorting and pagination
        query += f" ORDER BY {sort_by} {order} LIMIT ${param_index} OFFSET ${param_index + 1}"
        params.extend([limit, offset])
        
        rows = await self.db.fetch_all(query, *params)
        return [Product(**row) for row in rows]
    
    async def count_products_by_job(
        self,
        job_id: str,
        search_query: Optional[str] = None,
        src: Optional[str] = None
    ) -> int:
        """Count products for a job with filtering and search."""
        query = "SELECT COUNT(*) FROM products WHERE job_id = $1"
        params = [job_id]
        param_index = 2
        
        # Add src filter if provided
        if src:
            query += f" AND src = ${param_index}"
            params.append(src)
            param_index += 1
        
        # Add search filter if provided
        if search_query:
            query += f" AND (title ILIKE ${param_index} OR brand ILIKE ${param_index + 1} OR asin_or_itemid ILIKE ${param_index + 2})"
            search_pattern = f"%{search_query}%"
            params.extend([search_pattern, search_pattern, search_pattern])
        
        count = await self.db.fetch_val(query, *params)
        return count or 0
