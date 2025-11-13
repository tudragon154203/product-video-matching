import uuid
import time
from typing import Dict, Any, Optional, Set
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.logging_config import configure_logging
from collectors.base_product_collector import BaseProductCollector
from collectors.amazon_product_collector import AmazonProductCollector
from collectors.ebay.ebay_product_collector import EbayProductCollector
from config_loader import config
from .product_collection_manager import ProductCollectionManager
from .image_storage_manager import ImageStorageManager
from collectors.mock_ebay_collector import MockEbayCollector

logger = configure_logging("dropship-product-finder:service")


class DropshipProductFinderService:
    """Main service class for product collection"""

    def __init__(
        self,
        db: DatabaseManager,
        broker: MessageBroker,
        data_root: str,
        redis_client: Optional = None,
    ):
        self.db = db
        self.broker = broker
        self.redis = redis_client

        # Initialize collectors based on configuration
        if config.USE_MOCK_FINDERS:
            logger.info("Using mock product finders for development")

            self.collectors: Dict[str, BaseProductCollector] = {
                "amazon": AmazonProductCollector(data_root),
                "ebay": MockEbayCollector(data_root),
            }
        else:
            logger.info("Using real product finders (Amazon and eBay APIs)")
            self.collectors: Dict[str, BaseProductCollector] = {
                "amazon": AmazonProductCollector(data_root),
                "ebay": EbayProductCollector(
                    data_root=data_root, redis_client=self.redis
                ),
            }

        self.image_storage_manager = ImageStorageManager(db, broker, self.collectors)
        self.product_collection_manager = ProductCollectionManager(
            self.collectors, self.image_storage_manager
        )
        # Per-process idempotency guard for collections.completed emission
        self._collections_emitted: Set[str] = set()

    def update_redis_client(self, redis_client: Any) -> None:
        """Update the Redis client for the eBay collector."""
        self.redis = redis_client
        if not config.USE_MOCK_FINDERS and "ebay" in self.collectors:
            self.collectors["ebay"].update_redis_client(redis_client)
            logger.info("DropshipProductFinderService Redis client updated")

    async def handle_products_collect_request(self, event_data: Dict[str, Any], correlation_id: str):
        """Handle products collection request"""
        try:
            job_id = event_data["job_id"]
            queries = event_data["queries"]["en"]  # Use English queries
            top_amz = event_data["top_amz"]
            top_ebay = event_data["top_ebay"]
            start_time = time.perf_counter()

            logger.info(
                "Processing product collection request",
                job_id=job_id,
                query_count=len(queries),
            )

            (
                amazon_count,
                ebay_count,
            ) = await self.product_collection_manager.collect_and_store_products(
                job_id, queries, top_amz, top_ebay, correlation_id
            )

            total_images = (
                await self.db.fetch_val(
                    """
                    SELECT COUNT(*)
                    FROM product_images pi
                    JOIN products p ON pi.product_id = p.product_id
                    WHERE p.job_id = $1
                    """,
                    job_id,
                )
                or 0
            )

            logger.info(
                "Collected all products and images",
                job_id=job_id,
                amazon_count=amazon_count,
                ebay_count=ebay_count,
                total_images=total_images,
            )

            if total_images == 0:
                await self._handle_zero_products_case(job_id, correlation_id)
            else:
                await self._publish_all_image_events(job_id, total_images, correlation_id)

                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                logger.info(
                    "Completed product collection",
                    job_id=job_id,
                    amazon_count=amazon_count,
                    ebay_count=ebay_count,
                    total_images=total_images,
                    elapsed_ms=elapsed_ms,
                )

        except Exception as e:
            logger.error("Failed to process product collection request", error=str(e))
            raise

    async def _handle_zero_products_case(self, job_id: str, correlation_id: str):
        logger.info("No products found for job {job_id}", job_id=job_id)

        event_id = str(uuid.uuid4())
        await self.broker.publish_event(
            "products.collections.completed",
            {"job_id": job_id, "event_id": event_id},
            correlation_id=correlation_id,
        )

        vision_event_id = str(uuid.uuid4())
        await self.broker.publish_event(
            "products.images.ready.batch",
            {"job_id": job_id, "event_id": vision_event_id, "total_images": 0},
            correlation_id=correlation_id,
        )

        logger.info(
            "Published products.images.ready.batch with zero images",
            job_id=job_id,
            event_id=vision_event_id,
            total_images=0,
        )

        logger.info(
            "Skipping individual image events for job with no products", job_id=job_id
        )

    async def _publish_all_image_events(self, job_id: str, total_images: int, correlation_id: str):
        # Idempotency: ensure we only emit completion once per process for a given job_id
        if job_id in self._collections_emitted:
            logger.info(
                "Skipping duplicate products.collections.completed emission (idempotent guard)",
                job_id=job_id,
                total_images=total_images,
            )
            return
        self._collections_emitted.add(job_id)

        event_id = str(uuid.uuid4())
        await self.broker.publish_event(
            "products.collections.completed",
            {"job_id": job_id, "event_id": event_id},
            correlation_id=correlation_id,
        )
        logger.info(
            "Published products.collections.completed",
            job_id=job_id,
            event_id=event_id,
            total_images=total_images,
        )

        # Individual events are already published during processing
        # Just publish the batch event to signal completion
        vision_event_id = str(uuid.uuid4())
        await self.broker.publish_event(
            "products.images.ready.batch",
            {
                "job_id": job_id,
                "event_id": vision_event_id,
                "total_images": total_images,
            },
            correlation_id=correlation_id,
        )

        logger.info(
            "Published products.images.ready.batch",
            job_id=job_id,
            event_id=vision_event_id,
            total_images=total_images,
        )

    async def close(self):
        """Close all collectors"""
        for collector in self.collectors.values():
            await collector.close()
