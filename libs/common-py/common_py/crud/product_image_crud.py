from typing import Optional, List, Dict, Any
from ..database import DatabaseManager
from ..models import ProductImage
from ..logging_config import configure_logging

logger = configure_logging("common-py:product_image_crud")

class ProductImageCRUD:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def _convert_row_to_image(self, row: Dict[str, Any]) -> ProductImage:
        """Convert database row to ProductImage, handling vector types"""
        # Convert asyncpg.Record to dict to make it mutable
        row_dict = dict(row)

        # Convert vector strings back to lists if they exist
        if row_dict.get('emb_rgb') is not None:
            if isinstance(row_dict['emb_rgb'], str):
                # Parse string representation like "[0.1,0.2,0.3]"
                row_dict['emb_rgb'] = [float(x) for x in row_dict['emb_rgb'].strip('[]').split(',') if x]
        if row_dict.get('emb_gray') is not None:
            if isinstance(row_dict['emb_gray'], str):
                # Parse string representation like "[0.1,0.2,0.3]"
                row_dict['emb_gray'] = [float(x) for x in row_dict['emb_gray'].strip('[]').split(',') if x]
        return ProductImage(**row_dict)

    async def create_product_image(self, image: ProductImage) -> str:
        """Create a new product image with idempotent insert
        
        Returns:
            The image ID. If the image already exists, returns the provided img_id.
        """
        query = """
        INSERT INTO product_images (img_id, product_id, local_path, kp_blob_path, phash)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (img_id) DO NOTHING
        RETURNING img_id
        """
        inserted_id = await self.db.fetch_val(
            query,
            image.img_id,
            image.product_id,
            image.local_path,
            image.kp_blob_path,
            image.phash
        )
        if not inserted_id:
            # Conflict occurred; image already exists
            logger.debug(
                "Image already existed - idempotent insert skipped",
                img_id=image.img_id,
                product_id=image.product_id
            )
            return image.img_id
        return inserted_id

    async def update_embeddings(self, img_id: str, emb_rgb: List[float], emb_gray: List[float]):
        """Update embeddings for a product image"""
        # Convert lists to strings for pgvector compatibility
        emb_rgb_str = str(emb_rgb)
        emb_gray_str = str(emb_gray)
        query = """
        UPDATE product_images
        SET emb_rgb = $2::vector, emb_gray = $3::vector
        WHERE img_id = $1
        """
        await self.db.execute(query, img_id, emb_rgb_str, emb_gray_str)

    async def get_product_image(self, img_id: str) -> Optional[ProductImage]:
        """Get a product image by ID"""
        query = "SELECT * FROM product_images WHERE img_id = $1"
        row = await self.db.fetch_one(query, img_id)
        return self._convert_row_to_image(row) if row else None

    async def list_product_images(self, product_id: str) -> List[ProductImage]:
        """List images for a product"""
        query = "SELECT * FROM product_images WHERE product_id = $1"
        rows = await self.db.fetch_all(query, product_id)
        return [self._convert_row_to_image(row) for row in rows]

    async def list_product_images_by_job(
        self,
        job_id: str,
        product_id: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "created_at",
        order: str = "DESC",
        has_feature: Optional[str] = None
    ) -> List[ProductImage]:
        """List images for a job with filtering, search, pagination and sorting."""
        # Validate sort_by parameter
        valid_sort_fields = {"img_id", "created_at"}
        if sort_by not in valid_sort_fields:
            sort_by = "created_at"

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

        # Add feature filter if provided
        if has_feature:
            if has_feature == "segment":
                query += f" AND pi.masked_local_path IS NOT NULL"
            elif has_feature == "embedding":
                query += f" AND (pi.emb_rgb IS NOT NULL OR pi.emb_gray IS NOT NULL)"
            elif has_feature == "keypoints":
                query += f" AND pi.kp_blob_path IS NOT NULL"
            elif has_feature == "none":
                query += f" AND pi.masked_local_path IS NULL AND pi.emb_rgb IS NULL AND pi.emb_gray IS NULL AND pi.kp_blob_path IS NULL"
            elif has_feature == "any":
                query += f" AND (pi.masked_local_path IS NOT NULL OR pi.emb_rgb IS NOT NULL OR pi.emb_gray IS NOT NULL OR pi.kp_blob_path IS NOT NULL)"

        # Add sorting and pagination
        query += f" ORDER BY pi.{sort_by} {order} LIMIT ${param_index} OFFSET ${param_index + 1}"
        params.extend([limit, offset])

        rows = await self.db.fetch_all(query, *params)
        return [self._convert_row_to_image(row) for row in rows]

    async def count_product_images_by_job(
        self,
        job_id: str,
        product_id: Optional[str] = None,
        search_query: Optional[str] = None,
        has_feature: Optional[str] = None
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

        # Add feature filter if provided
        if has_feature:
            if has_feature == "segment":
                query += f" AND pi.masked_local_path IS NOT NULL"
            elif has_feature == "embedding":
                query += f" AND (pi.emb_rgb IS NOT NULL OR pi.emb_gray IS NOT NULL)"
            elif has_feature == "keypoints":
                query += f" AND pi.kp_blob_path IS NOT NULL"
            elif has_feature == "none":
                query += f" AND pi.masked_local_path IS NULL AND pi.emb_rgb IS NULL AND pi.emb_gray IS NULL AND pi.kp_blob_path IS NULL"
            elif has_feature == "any":
                query += f" AND (pi.masked_local_path IS NOT NULL OR pi.emb_rgb IS NOT NULL OR pi.emb_gray IS NOT NULL OR pi.kp_blob_path IS NOT NULL)"

        count = await self.db.fetch_val(query, *params)
        return count or 0

    async def list_product_images_by_job_with_features(
        self,
        job_id: str,
        has_feature: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "created_at",
        order: str = "DESC"
    ) -> List[ProductImage]:
        """List images for a job with feature filtering, pagination and sorting."""
        # Validate sort_by parameter
        valid_sort_fields = {"img_id", "created_at"}
        if sort_by not in valid_sort_fields:
            sort_by = "created_at"

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

        # Add feature filter if provided
        if has_feature:
            if has_feature == "segment":
                query += f" AND pi.masked_local_path IS NOT NULL"
            elif has_feature == "embedding":
                query += f" AND (pi.emb_rgb IS NOT NULL OR pi.emb_gray IS NOT NULL)"
            elif has_feature == "keypoints":
                query += f" AND pi.kp_blob_path IS NOT NULL"
            elif has_feature == "none":
                query += f" AND pi.masked_local_path IS NULL AND pi.emb_rgb IS NULL AND pi.emb_gray IS NULL AND pi.kp_blob_path IS NULL"
            elif has_feature == "any":
                query += f" AND (pi.masked_local_path IS NOT NULL OR pi.emb_rgb IS NOT NULL OR pi.emb_gray IS NOT NULL OR pi.kp_blob_path IS NOT NULL)"

        # Add sorting and pagination
        query += f" ORDER BY pi.{sort_by} {order} LIMIT ${param_index} OFFSET ${param_index + 1}"
        params.extend([limit, offset])

        rows = await self.db.fetch_all(query, *params)
        return [self._convert_row_to_image(row) for row in rows]

    async def create_product_image_with_conn(self, image: ProductImage, conn) -> str:
        """
        Create a new product image using an existing asyncpg connection.
        Idempotent via ON CONFLICT (img_id) DO NOTHING.

        Args:
            image: ProductImage model to insert
            conn: Existing asyncpg connection to execute against

        Returns:
            The image ID. If the image already exists, returns the provided img_id.
        """
        query = """
        INSERT INTO product_images (img_id, product_id, local_path, kp_blob_path, phash)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (img_id) DO NOTHING
        RETURNING img_id
        """
        inserted_id = await conn.fetchval(
            query,
            image.img_id,
            image.product_id,
            image.local_path,
            image.kp_blob_path,
            image.phash
        )
        if not inserted_id:
            # Conflict occurred; image already exists
            logger.debug(
                "Image already existed - idempotent insert skipped",
                img_id=image.img_id,
                product_id=image.product_id
            )
            return image.img_id
        return inserted_id