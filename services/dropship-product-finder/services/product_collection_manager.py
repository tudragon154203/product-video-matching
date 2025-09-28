from typing import Dict, List
import asyncio
from common_py.logging_config import configure_logging
from collectors.interface import IProductCollector
from .image_storage_manager import ImageStorageManager

logger = configure_logging("dropship-product-finder:product_collection_manager")


class ProductCollectionManager:
    def __init__(
        self,
        collectors: Dict[str, IProductCollector],
        image_storage_manager: ImageStorageManager,
    ):
        self.collectors = collectors
        self.image_storage_manager = image_storage_manager

    async def collect_and_store_products(
        self, job_id: str, queries: List[str], top_amz: int, top_ebay: int
    ) -> tuple[int, int]:
        async def _process_platform(platform: str, top_k: int) -> int:
            count = 0
            logger.info("[%s] Worker START job=%s", platform, job_id)

            for query in queries:
                try:
                    products = await self.collectors[platform].collect_products(
                        query, top_k
                    )
                except Exception as e:
                    product_id = "unknown"
                    logger.exception(
                        "[%s] Collect failed for query='%s' (id=%s): %s",
                        platform,
                        query,
                        product_id,
                        e,
                    )
                    continue

                for product_data in products:
                    try:
                        await self.image_storage_manager.store_product(
                            product_data, job_id, platform
                        )
                        count += 1
                    except Exception as e:
                        product_id = product_data.get(
                            "id", product_data.get("sku", "unknown")
                        )
                        logger.exception(
                            "[%s] Store failed (id=%s) for query='%s': %s",
                            platform,
                            product_id,
                            query,
                            e,
                        )

            logger.info(
                "[%s] Worker END job=%s, count=%s", platform, job_id, count
            )
            return count

        # Create exactly 2 parallel tasks for Amazon and eBay
        amazon_task = asyncio.create_task(_process_platform("amazon", top_amz))
        ebay_task = asyncio.create_task(_process_platform("ebay", top_ebay))

        # Wait for both workers to complete
        amazon_count, ebay_count = await asyncio.gather(amazon_task, ebay_task)

        logger.info(
            "Job %s completed: Amazon=%s, eBay=%s",
            job_id,
            amazon_count,
            ebay_count,
        )
        return amazon_count, ebay_count
