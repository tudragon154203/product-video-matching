"""Core service layer for the evidence builder."""

from typing import Any, Dict

from common_py.database import DatabaseManager
from common_py.logging_config import configure_logging
from common_py.messaging import MessageBroker

from evidence import EvidenceGenerator

from .evidence_publisher import EvidencePublisher
from .match_record_manager import MatchRecordManager

logger = configure_logging("evidence-builder:service")


class EvidenceBuilderService:
    """Coordinate evidence generation and publication flows."""

    def __init__(
        self,
        db: DatabaseManager,
        broker: MessageBroker,
        data_root: str,
    ) -> None:
        self.db = db
        self.broker = broker
        self.evidence_generator = EvidenceGenerator(data_root)
        self.match_record_manager = MatchRecordManager(db)
        self.evidence_publisher = EvidencePublisher(broker, db)

    async def handle_match_result(self, event_data: Dict[str, Any]) -> None:
        """Handle match result event and generate evidence."""
        job_id = event_data.get("job_id")
        product_id = event_data.get("product_id")
        video_id = event_data.get("video_id")
        best_pair = event_data.get("best_pair")
        score = event_data.get("score")
        timestamp = event_data.get("ts")

        if None in {job_id, product_id, video_id, best_pair, score, timestamp}:
            raise ValueError("match.result event is missing required fields")

        logger.info(
            "Processing match result for evidence",
            job_id=job_id,
            product_id=product_id,
            video_id=video_id,
            score=score,
        )

        img_id = best_pair.get("img_id") if isinstance(best_pair, dict) else None
        frame_id = best_pair.get("frame_id") if isinstance(best_pair, dict) else None
        if not img_id or not frame_id:
            raise ValueError("match.result best_pair must contain img_id and frame_id")

        image_info = await self.match_record_manager.get_image_info(img_id)
        frame_info = await self.match_record_manager.get_frame_info(frame_id)

        if not image_info or not frame_info:
            logger.error(
                "Failed to get image or frame info",
                img_id=img_id,
                frame_id=frame_id,
            )
            return

        evidence_path = self.evidence_generator.create_evidence(
            image_path=image_info["local_path"],
            frame_path=frame_info["local_path"],
            img_id=img_id,
            frame_id=frame_id,
            score=float(score),
            timestamp=float(timestamp),
            kp_img_path=image_info.get("kp_blob_path"),
            kp_frame_path=frame_info.get("kp_blob_path"),
        )

        if evidence_path:
            await self.match_record_manager.update_match_record_and_log(
                job_id,
                product_id,
                video_id,
                evidence_path,
            )
            await self.evidence_publisher.publish_evidence_completion_if_needed(job_id)
        else:
            logger.error(
                "Failed to generate evidence",
                job_id=job_id,
                product_id=product_id,
                video_id=video_id,
            )

    async def handle_matchings_completed(
        self,
        event_data: Dict[str, Any],
    ) -> None:
        """Handle matchings completed event, covering zero-match jobs."""
        await self.evidence_publisher.handle_matchings_completed(event_data)
