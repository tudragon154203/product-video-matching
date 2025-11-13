from typing import Dict, List
import asyncio
from common_py.logging_config import configure_logging
from collectors.interface import IProductCollector
from .image_storage_manager import ImageStorageManager
from config_loader import config

logger = configure_logging("dropship-product-finder:product_collection_manager")


class ProductCollectionManager:
    def __init__(
        self,
        collectors: Dict[str, IProductCollector],
        image_storage_manager: ImageStorageManager,
    ):
        self.collectors = collectors
        self.image_storage_manager = image_storage_manager
        # Minimal observability of performance knobs
        logger.info(
            "dropship-product-finder performance: browse_concurrency=%s, item_concurrency=%s, image_timeout_s=%s",
            config.BROWSE_CONCURRENCY,
            config.ITEM_CONCURRENCY,
            config.IMAGE_DOWNLOAD_TIMEOUT_SECS,
        )

    async def collect_and_store_products(
        self, job_id: str, queries: List[str], top_amz: int, top_ebay: int, correlation_id: str
    ) -> tuple[int, int]:
        browse_sema = asyncio.Semaphore(config.BROWSE_CONCURRENCY)
        item_sema = asyncio.Semaphore(config.ITEM_CONCURRENCY)

        async def _process_platform(platform: str, top_k: int) -> int:
            current_correlation_id = correlation_id
            logger.info("[%s] Worker START job=%s", platform, job_id)

            async def process_query(query: str) -> int:
                # Bound browse (search/detail) calls per query
                async with browse_sema:
                    try:
                        products = await self.collectors[platform].collect_products(query, top_k)
                    except Exception as e:
                        # Ensure one query failure doesn't block others
                        logger.exception(
                            "[%s] Collect failed for query='%s': %s",
                            platform,
                            query,
                            e,
                        )
                        return 0

                async def process_item(product_data: Dict) -> int:
                    # Bound per-item detail/store steps
                    async with item_sema:
                        try:
                            await self.image_storage_manager.store_product(
                                product_data, job_id, platform, current_correlation_id
                            )
                            return 1
                        except Exception as e:
                            product_id = product_data.get("id", product_data.get("sku", "unknown"))
                            logger.exception(
                                "[%s] Store failed (id=%s) for query='%s': %s",
                                platform,
                                product_id,
                                query,
                                e,
                            )
                            return 0

                # Schedule bounded per-item tasks
                item_tasks = [asyncio.create_task(process_item(pd)) for pd in products]
                # Centralized gather; exceptions handled in process_item
                item_results = await asyncio.gather(*item_tasks, return_exceptions=False)
                return sum(item_results)

            # Schedule bounded per-query tasks
            query_tasks = [asyncio.create_task(process_query(q)) for q in queries]
            # Centralized gather; exceptions handled in process_query
            per_query_counts = await asyncio.gather(*query_tasks, return_exceptions=False)
            total_count = sum(per_query_counts)

            logger.info("[%s] Worker END job=%s, count=%s", platform, job_id, total_count)
            return total_count

        # Two platform workers gathered together
        amazon_task = asyncio.create_task(_process_platform("amazon", top_amz))
        ebay_task = asyncio.create_task(_process_platform("ebay", top_ebay))

        amazon_count, ebay_count = await asyncio.gather(amazon_task, ebay_task)

        logger.info(
            "Job %s completed: Amazon=%s, eBay=%s",
            job_id,
            amazon_count,
            ebay_count,
        )
        return amazon_count, ebay_count
