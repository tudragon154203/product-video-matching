from common_py.messaging import MessageBroker
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class BrokerHandler:
    def __init__(self, broker: MessageBroker):
        self.broker = broker

    async def publish_product_collection_request(self, job_id: str, top_amz: int, top_ebay: int, queries: Dict[str, Any]):
        """Publish a product collection request."""
        try:
            await self.broker.publish_event(
                "products.collect.request",
                {
                    "job_id": job_id,
                    "top_amz": top_amz,
                    "top_ebay": top_ebay,
                    "queries": queries
                },
                correlation_id=job_id
            )
        except Exception as e:
            logger.warning(f"Failed to publish product collection request: {e}")
            raise

    async def publish_video_search_request(self, job_id: str, industry: str, queries: Dict[str, Any], platforms: list, recency_days: int):
        """Publish a video search request."""
        try:
            await self.broker.publish_event(
                "videos.search.request",
                {
                    "job_id": job_id,
                    "industry": industry,
                    "queries": queries,
                    "platforms": platforms,
                    "recency_days": recency_days,
                },
                correlation_id=job_id
            )
        except Exception as e:
            logger.warning(f"Failed to publish video search request: {e}")
            raise

    async def publish_match_request(self, job_id: str, industry: str, product_set_id: str, video_set_id: str):
        """Publish a match request."""
        try:
            await self.broker.publish_event(
                "match.request",
                {
                    "job_id": job_id,
                    "industry": industry,
                    "product_set_id": product_set_id,
                    "video_set_id": video_set_id,
                    "top_k": 20
                },
                correlation_id=job_id
            )
            logger.info(f"Published match request for job {job_id}")
        except Exception as e:
            logger.error(f"Failed to publish match request for job {job_id}: {str(e)}")
            raise

    async def publish_job_completed(self, job_id: str):
        """Publish a job completion event."""
        try:
            await self.broker.publish_event(
                "job.completed",
                {
                    "job_id": job_id
                },
                correlation_id=job_id
            )
            logger.info(f"Published job completion for job {job_id}")
        except Exception as e:
            logger.error(f"Failed to publish job completion for job {job_id}: {str(e)}")
            raise