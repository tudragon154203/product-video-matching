from typing import Optional
from datetime import datetime, timezone
import pytz

from common_py.database import DatabaseManager
from common_py.crud.product_crud import ProductCRUD
from common_py.crud.product_image_crud import ProductImageCRUD
from models.schemas import ProductItem, ProductListResponse
from utils.product_utils import select_primary_images
from config_loader import config


class ProductService:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.product_crud = ProductCRUD(db)
        self.product_image_crud = ProductImageCRUD(db)

    def _get_gmt7_time(self, dt: Optional[datetime]) -> Optional[datetime]:
        """Convert datetime to GMT+7 timezone"""
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(pytz.timezone('Asia/Ho_Chi_Minh'))

    async def get_job_products(
        self,
        job_id: str,
        search_query: Optional[str] = None,
        src: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "updated_at",
        order: str = "DESC"
    ) -> ProductListResponse:
        """
        Get products for a specific job with filtering and pagination.

        Args:
            job_id: The job ID to filter products by
            search_query: Search query for product titles, brands, or ASIN/ItemID
            src: Filter by source platform (e.g., 'amazon', 'ebay')
            limit: Maximum number of items to return
            offset: Number of items to skip for pagination
            sort_by: Field to sort by
            order: Sort order (ASC or DESC)

        Returns:
            ProductListResponse: Paginated list of products matching the criteria
        """
        # Get products with filtering and pagination
        products = await self.product_crud.list_products_by_job(
            job_id=job_id,
            search_query=search_query,
            src=src,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            order=order
        )

        # Get total count for pagination
        total = await self.product_crud.count_products_by_job(
            job_id=job_id,
            search_query=search_query,
            src=src
        )

        # Convert to response format and get image counts
        product_items = []
        for product in products:
            # Get primary image and image count for this product
            primary_image_url, image_count = await select_primary_images(
                product.product_id,
                self.product_image_crud,
                config.DATA_ROOT_CONTAINER
            )

            product_item = ProductItem(
                product_id=product.product_id,
                src=product.src,
                asin_or_itemid=product.asin_or_itemid,
                title=product.title,
                brand=product.brand,
                url=product.url,
                image_count=image_count,
                created_at=self._get_gmt7_time(product.created_at),
                primary_image_url=primary_image_url
            )
            product_items.append(product_item)

        return ProductListResponse(
            items=product_items,
            total=total,
            limit=limit,
            offset=offset
        )
