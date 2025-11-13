import uuid
import asyncio
import time
from typing import Dict, Any, List
import asyncpg
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.crud import ProductCRUD, ProductImageCRUD
from common_py.models import Product, ProductImage
from common_py.logging_config import configure_logging
from collectors.base_product_collector import BaseProductCollector

logger = configure_logging("dropship-product-finder:image_storage_manager")


class ImageStorageManager:
    def __init__(
        self,
        db: DatabaseManager,
        broker: MessageBroker,
        collectors: Dict[str, BaseProductCollector],
    ):
        self.db = db
        self.broker = broker
        self.product_crud = ProductCRUD(db)
        self.image_crud = ProductImageCRUD(db)
        self.collectors = collectors

    async def store_product(
        self, product_data: Dict[str, Any], job_id: str, source: str, correlation_id: str
    ):
        """Store a single product and its images within a single transaction on one DB connection.

        Ensures product insert and subsequent image inserts are atomic to avoid FK violations.
        Defers publishing image.ready events until after COMMIT to avoid race conditions.
        """
        start_time = time.perf_counter()
        images = product_data.get("images", [])
        # Determine marketplace based on source (default to 'us' for mock data)
        marketplace = "us"  # Default marketplace for mock data

        product = Product(
            product_id=str(uuid.uuid4()),
            src=source,
            asin_or_itemid=product_data["id"],
            title=product_data["title"],
            brand=product_data.get("brand"),
            url=product_data["url"],
            marketplace=marketplace,
            job_id=job_id,
        )

        if not self.db.pool:
            raise RuntimeError("Database not connected")

        async with self.db.pool.acquire() as conn:
            try:
                # Explicit transaction to guarantee single-connection ordering
                await conn.execute("BEGIN")
                logger.info(
                    "BEGIN product+images transaction",
                    job_id=job_id,
                    product_id=product.product_id,
                    images_count=len(images),
                )

                # Insert product row using the same connection
                await conn.execute(
                    """
                    INSERT INTO products (
                        product_id,
                        src,
                        asin_or_itemid,
                        title,
                        brand,
                        url,
                        marketplace,
                        job_id
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    product.product_id,
                    product.src,
                    product.asin_or_itemid,
                    product.title,
                    product.brand,
                    product.url,
                    product.marketplace,
                    job_id,
                )

                # Insert images using same connection with FK-violation-aware retry
                events_to_publish: List[Dict[str, Any]] = []
                await self._download_and_store_product_images(
                    product, images, source, job_id, correlation_id, conn, events_to_publish
                )

                # Commit transaction
                await conn.execute("COMMIT")
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                logger.info(
                    "COMMIT product+images transaction",
                    job_id=job_id,
                    product_id=product.product_id,
                    images_count=len(images),
                    elapsed_ms=elapsed_ms,
                )

                # Publish buffered events after commit
                for evt in events_to_publish:
                    await self.broker.publish_event(
                        evt["topic"], evt["payload"], correlation_id=evt["correlation_id"]
                    )
                    logger.info(
                        "Published individual image ready event",
                        product_id=evt["payload"].get("product_id"),
                        image_id=evt["payload"].get("image_id"),
                        job_id=evt["payload"].get("job_id"),
                    )
            except Exception as e:
                # Rollback on any failure and re-raise
                try:
                    await conn.execute("ROLLBACK")
                except Exception as rb_err:
                    logger.error("ROLLBACK failed", job_id=job_id, error=str(rb_err))
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                logger.error(
                    "Transaction failed - rolling back",
                    job_id=job_id,
                    product_id=product.product_id,
                    images_count=len(images),
                    elapsed_ms=elapsed_ms,
                    error=str(e),
                )
                raise

    async def _download_and_store_product_images(
        self,
        product: Product,
        image_urls: List[str],
        source: str,
        job_id: str,
        correlation_id: str,
        conn: asyncpg.Connection,
        events_buffer: List[Dict[str, Any]],
    ):
        """
        Download images and store them using the provided DB connection.
        Resilient to FK violations via bounded retry that polls for product existence.
        """
        # Retry/backoff settings
        base_delay = 0.2
        backoff_factor = 2.0
        max_delay = 2.0
        deadline_s = 20.0

        for i, image_url in enumerate(image_urls):
            image_id = f"{product.product_id}_img_{i}"
            try:
                local_path = await self.collectors[source].download_image(
                    image_url, product.product_id, image_id
                )
            except Exception as dl_err:
                logger.error(
                    "Failed to download image",
                    product_id=product.product_id,
                    image_id=image_id,
                    image_url=image_url,
                    error=str(dl_err),
                )
                continue

            if not local_path:
                logger.error(
                    "Collector returned empty local_path for image",
                    product_id=product.product_id,
                    image_id=image_id,
                    image_url=image_url,
                )
                continue

            image = ProductImage(
                img_id=image_id,
                product_id=product.product_id,
                local_path=local_path,
            )

            # Try idempotent insert; on FK violation, poll for product existence with backoff
            start_time = time.perf_counter()
            delay = base_delay
            while True:
                try:
                    # Use connection-scoped insert for atomicity
                    await self.image_crud.create_product_image_with_conn(image, conn)

                    # Buffer event for post-commit publishing
                    events_buffer.append(
                        {
                            "topic": "products.image.ready",
                            "payload": {
                                "product_id": product.product_id,
                                "image_id": image_id,
                                "local_path": local_path,
                                "job_id": job_id,
                            },
                            "correlation_id": correlation_id,
                        }
                    )
                    break
                except Exception as e:
                    # Detect FK violation by SQLSTATE or message text
                    msg = str(e).lower()
                    is_fk_violation = (
                        "foreign key" in msg
                        or "23503" in msg  # SQLSTATE for FK violation
                        or isinstance(e, asyncpg.ForeignKeyViolationError)
                    )
                    elapsed = time.perf_counter() - start_time
                    if not is_fk_violation or elapsed >= deadline_s:
                        logger.error(
                            "Image insert failed (not retriable or deadline exceeded)",
                            job_id=job_id,
                            product_id=product.product_id,
                            image_id=image_id,
                            image_url=image_url,
                            error=str(e),
                            elapsed_s=round(elapsed, 3),
                        )
                        # Skip or abort per existing policy: skip this image
                        break

                    # Poll for product existence before retrying
                    try:
                        exists = await conn.fetchval(
                            "SELECT 1 FROM products WHERE product_id = $1",
                            product.product_id,
                        )
                    except Exception as poll_err:
                        exists = None
                        logger.error(
                            "Product existence poll failed",
                            job_id=job_id,
                            product_id=product.product_id,
                            error=str(poll_err),
                        )

                    if exists:
                        # Exponential backoff before retrying insert
                        await asyncio.sleep(delay)
                        delay = min(delay * backoff_factor, max_delay)
                    else:
                        # If product still not visible, wait then continue polling
                        await asyncio.sleep(delay)
                        delay = min(delay * backoff_factor, max_delay)
