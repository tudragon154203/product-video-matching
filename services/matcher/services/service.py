"""Core matching service orchestration."""

import uuid
from typing import Any, Dict, List

from common_py.crud import EventCRUD, MatchCRUD
from common_py.database import DatabaseManager
from common_py.logging_config import configure_logging
from common_py.messaging import MessageBroker
from common_py.models import Match

from matching import MatchingEngine

logger = configure_logging("matcher:service")


class MatcherService:
    """High-level coordination for matching jobs."""

    def __init__(
        self,
        db: DatabaseManager,
        broker: MessageBroker,
        data_root: str,
        **params: Any,
    ) -> None:
        self.db = db
        self.broker = broker
        self.event_crud = EventCRUD(db)
        self.match_crud = MatchCRUD(db)
        self.matching_engine = MatchingEngine(db, data_root, **params)

    async def initialize(self) -> None:
        """Initialise the matching engine."""

        await self.matching_engine.initialize()

    async def cleanup(self) -> None:
        """Clean up resources held by the matching engine."""

        await self.matching_engine.cleanup()

    async def handle_match_request(self, event_data: Dict[str, Any]) -> None:
        """Handle a match request event by running the matching pipeline."""

        try:
            job_id = event_data["job_id"]
            event_id = event_data["event_id"]

            # Check idempotency - if this event has been processed, return early
            if await self.event_crud.is_event_processed(event_id):
                logger.info(
                    "Match request already processed, skipping due to idempotency",
                    job_id=job_id,
                    event_id=event_id,
                )
                return

            logger.info(
                "Processing match request",
                job_id=job_id,
                event_id=event_id,
            )

            products = await self.get_job_products(job_id)
            videos = await self.get_job_videos(job_id)

            logger.info(
                "Found entities for matching",
                job_id=job_id,
                product_count=len(products),
                video_count=len(videos),
            )

            total_matches = 0
            for product in products:
                for video in videos:
                    match_product_video = (
                        self.matching_engine.match_product_video
                    )
                    match_result = await match_product_video(
                        product["product_id"],
                        video["video_id"],
                        job_id,
                    )

                    if not match_result:
                        continue

                    match = Match(
                        match_id=str(uuid.uuid4()),
                        job_id=job_id,
                        product_id=product["product_id"],
                        video_id=video["video_id"],
                        best_img_id=match_result["best_img_id"],
                        best_frame_id=match_result["best_frame_id"],
                        ts=match_result["ts"],
                        score=match_result["score"],
                    )

                    await self.match_crud.create_match(match)

                    await self.broker.publish_event(
                        "match.result",
                        {
                            "job_id": job_id,
                            "product_id": product["product_id"],
                            "video_id": video["video_id"],
                            "best_pair": {
                                "img_id": match_result["best_img_id"],
                                "frame_id": match_result["best_frame_id"],
                                "score_pair": match_result["best_pair_score"],
                            },
                            "score": match_result["score"],
                            "ts": match_result["ts"],
                        },
                        correlation_id=job_id,
                    )

                    total_matches += 1

                    logger.info(
                        "Found match",
                        job_id=job_id,
                        product_id=product["product_id"],
                        video_id=video["video_id"],
                        score=match_result["score"],
                    )

            await self.broker.publish_event(
                "matchings.process.completed",
                {
                    "job_id": job_id,
                    "event_id": event_id,
                },
                correlation_id=job_id,
            )

            # Update job phase to evidence after matching completes
            await self.db.execute(
                "UPDATE jobs SET phase = 'evidence' WHERE job_id = $1",
                job_id
            )

            # Record this event_id as processed to ensure idempotency
            await self.event_crud.record_event(event_id, "match.request")

            logger.info(
                "Completed matching",
                job_id=job_id,
                total_matches=total_matches,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to process match request", error=str(exc))
            raise

    async def get_job_products(self, job_id: str) -> List[Dict[str, Any]]:
        """Fetch all products associated with a job."""

        query = """
        SELECT DISTINCT p.product_id, p.title
        FROM products p
        WHERE p.job_id = $1
        """
        return await self.db.fetch_all(query, job_id)

    async def get_job_videos(self, job_id: str) -> List[Dict[str, Any]]:
        """Fetch all videos associated with a job."""

        query = """
        SELECT DISTINCT v.video_id, v.title
        FROM videos v
        JOIN job_videos jv ON jv.video_id = v.video_id
        WHERE jv.job_id = $1
        """
        return await self.db.fetch_all(query, job_id)
