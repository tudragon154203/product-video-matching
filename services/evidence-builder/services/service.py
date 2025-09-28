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
        try:
            job_id = event_data["job_id"]
            product_id = event_data["product_id"]
            video_id = event_data["video_id"]
            best_pair = event_data["best_pair"]
            score = event_data["score"]
            timestamp = event_data["ts"]

            logger.info(
                "Processing match result for evidence",
                job_id=job_id,
                product_id=product_id,
                video_id=video_id,
                score=score,
            )

            image_info = await self.match_record_manager.get_image_info(
                best_pair["img_id"]
            )
            frame_info = await self.match_record_manager.get_frame_info(
                best_pair["frame_id"]
            )

            if not image_info or not frame_info:
                logger.error(
                    "Failed to get image or frame info",
                    img_id=best_pair["img_id"],
                    frame_id=best_pair["frame_id"],
                )
                return

            evidence_path = self.evidence_generator.create_evidence(
                image_path=image_info["local_path"],
                frame_path=frame_info["local_path"],
                img_id=best_pair["img_id"],
                frame_id=best_pair["frame_id"],
                score=score,
                timestamp=timestamp,
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
                await self.evidence_publisher.publish_evidence_completion_if_needed(
                    job_id
                )
            else:
                logger.error(
                    "Failed to generate evidence",
                    job_id=job_id,
                    product_id=product_id,
                    video_id=video_id,
                )

        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to process match result", error=str(exc))
            raise

    async def handle_matchings_completed(
        self,
        event_data: Dict[str, Any],
    ) -> None:
        """Handle matchings completed event, covering zero-match jobs."""
        await self.evidence_publisher.handle_matchings_completed(event_data)
