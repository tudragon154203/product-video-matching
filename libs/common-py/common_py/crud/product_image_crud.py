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
    
    async def list_product_images_by_job(
        self,
        job_id: str,
        product_id: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "updated_at",
        order: str = "DESC"
    ) -> List[ProductImage]:
        """List images for a job with filtering, search, pagination and sorting."""
        # Validate sort_by parameter
        valid_sort_fields = {"img_id", "updated_at"}
        if sort_by not in valid_sort_fields:
            sort_by = "updated_at"
        
        # Validate order parameter
        order = order.upper()
        if order not in {"ASC", "DESC"}:
            order = "DESC"
        
        # Build query with filters
        query = """
            SELECT pi.*, p.title as product_title
            FROM product_images pi
            JOIN products p ON pi.product_id = p.product_id
            WHERE p.job_id = $1
        """
        params = [job_id]
        param_index = 2
        
        # Add product_id filter if provided
        if product_id:
            query += f" AND pi.product_id = ${param_index}"
            params.append(product_id)
            param_index += 1
        
        # Add search filter if provided
        if search_query:
            query += f" AND (pi.img_id ILIKE ${param_index} OR p.title ILIKE ${param_index})"
            params.append(f"%{search_query}%")
            param_index += 1
        
        # Add sorting and pagination
        query += f" ORDER BY pi.{sort_by} {order} LIMIT ${param_index} OFFSET ${param_index + 1}"
        params.extend([limit, offset])
        
        rows = await self.db.fetch_all(query, *params)
        return [ProductImage(**row) for row in rows]
    
    async def count_product_images_by_job(
        self,
        job_id: str,
        product_id: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> int:
        """Count images for a job with filtering and search."""
        query = """
            SELECT COUNT(*)
            FROM product_images pi
            JOIN products p ON pi.product_id = p.product_id
            WHERE p.job_id = $1
        """
        params = [job_id]
        param_index = 2
        
        # Add product_id filter if provided
        if product_id:
            query += f" AND pi.product_id = ${param_index}"
            params.append(product_id)
            param_index += 1
        
        # Add search filter if provided
        if search_query:
            query += f" AND (pi.img_id ILIKE ${param_index} OR p.title ILIKE ${param_index})"
            params.append(f"%{search_query}%")
            param_index += 1
        
        count = await self.db.fetch_val(query, *params)
        return count or 0
