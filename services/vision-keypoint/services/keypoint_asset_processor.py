import uuid

from common_py.database import DatabaseManager
from common_py.logging_config import configure_logging
from common_py.messaging import MessageBroker

from keypoint import KeypointExtractor
from vision_common import JobProgressManager

logger = configure_logging("vision-keypoint:keypoint_asset_processor")


class KeypointAssetProcessor:
    def __init__(
        self,
        db: DatabaseManager,
        broker: MessageBroker,
        extractor: KeypointExtractor,
        progress_manager: JobProgressManager,
    ):
        self.db = db
        self.broker = broker
        self.extractor = extractor
        self.progress_manager = progress_manager

    async def process_single_asset(
        self,
        job_id: str,
        asset_id: str,
        asset_type: str,
        local_path: str,
        is_masked: bool = False,
        mask_path: str | None = None,
    ) -> bool:
        """Common single asset processing logic for keypoint extraction."""
        asset_key = f"{job_id}:{asset_id}"

        if asset_key in self.progress_manager.processed_assets:
            logger.info(
                "Skipping duplicate asset",
                job_id=job_id,
                asset_id=asset_id,
                asset_type=asset_type,
            )
            return False

        self.progress_manager.processed_assets.add(asset_key)

        logger.info(
            "Processing item",
            job_id=job_id,
            asset_id=asset_id,
            asset_type=asset_type,
            item_path=local_path,
            operation=(
                "masked_keypoint_extraction" if is_masked else "keypoint_extraction"
            ),
        )

        kp_blob_path = None
        if is_masked and mask_path:
            # Get the original image/frame path from database
            if asset_type == "image":
                result = await self.db.fetch_one(
                    "SELECT local_path FROM product_images WHERE img_id = $1",
                    asset_id,
                )
            else:  # video frame
                result = await self.db.fetch_one(
                    "SELECT local_path FROM video_frames WHERE frame_id = $1",
                    asset_id,
                )

            if not result:
                logger.error(
                    "Resource not found",
                    job_id=job_id,
                    asset_id=asset_id,
                    asset_type=asset_type,
                    resource_type="original_asset_record",
                )
                return False

            original_local_path = result["local_path"]
            kp_blob_path = await self.extractor.extract_keypoints_with_mask(
                original_local_path, mask_path, asset_id
            )
        else:
            kp_blob_path = await self.extractor.extract_keypoints(local_path, asset_id)

        if kp_blob_path:
            # Update database with keypoint path
            if asset_type == "image":
                await self.db.execute(
                    "UPDATE product_images SET kp_blob_path = $1 WHERE img_id = $2",
                    kp_blob_path,
                    asset_id,
                )
            else:  # video frame
                await self.db.execute(
                    "UPDATE video_frames SET kp_blob_path = $1 WHERE frame_id = $2",
                    kp_blob_path,
                    asset_id,
                )

            # Emit keypoint ready event (per asset)
            event_id = str(uuid.uuid4())
            await self.broker.publish_event(
                f"{asset_type}.keypoint.ready",
                {
                    "job_id": job_id,
                    "asset_id": asset_id,
                    "event_id": event_id,
                },
            )

            logger.info(
                "Item processed successfully",
                job_id=job_id,
                asset_id=asset_id,
                asset_type=asset_type,
            )
            return True
        else:
            logger.error(
                "Item processing failed",
                job_id=job_id,
                asset_id=asset_id,
                asset_type=asset_type,
                error="Failed to extract keypoints",
            )
            return False

    async def update_and_check_completion_per_asset_first(
        self, job_id: str, asset_type: str
    ):
        """Update progress and check if batch is complete (per-asset first pattern)."""
        if job_id not in self.progress_manager.job_tracking:
            logger.info(
                "Initializing job tracking with high expected count (per-asset first)",
                job_id=job_id,
                asset_type=asset_type,
            )
            await self.progress_manager.initialize_with_high_expected(
                job_id, asset_type, event_type_prefix="keypoints"
            )

        await self.progress_manager.update_job_progress(
            job_id,
            asset_type,
            0,
            increment=1,
            event_type_prefix="keypoints",
        )

        if self.progress_manager._is_batch_initialized(job_id, asset_type):
            if asset_type == "image":
                job_counts = self.progress_manager.job_image_counts.get(job_id)
                real_expected = job_counts["total"] if job_counts else 0
            else:
                real_expected = self.progress_manager.expected_total_frames.get(
                    job_id, 0
                )

            if real_expected > 0:
                logger.info(
                    "Batch initialized, updating with real expected count",
                    job_id=job_id,
                    asset_type=asset_type,
                    real_expected=real_expected,
                )
                await self.progress_manager.update_expected_and_recheck_completion(
                    job_id,
                    asset_type,
                    real_expected,
                    "keypoints",
                )

    async def handle_batch_initialization(
        self,
        job_id: str,
        asset_type: str,
        total_items: int,
        event_type: str,
        event_id: str | None = None,
    ):
        """Common batch initialization logic."""
        logger.info(
            "Batch event received",
            job_id=job_id,
            asset_type=asset_type,
            total_items=total_items,
            event_type=event_type,
        )

        if asset_type == "image":
            self.progress_manager.job_image_counts[job_id] = {
                "total": total_items,
                "processed": 0,
            }
        else:
            self.progress_manager.expected_total_frames[job_id] = total_items
            self.progress_manager.job_frame_counts[job_id] = {
                "total": total_items,
                "processed": 0,
            }

        logger.info(
            "Batch tracking initialized",
            job_id=job_id,
            asset_type=asset_type,
            total_items=total_items,
        )

        self.progress_manager._mark_batch_initialized(job_id, asset_type)

        if total_items == 0:
            logger.info(
                "Zero-asset job, ensuring tracking exists and triggering completion",
                job_id=job_id,
                asset_type=asset_type,
            )
            key = f"{job_id}:{asset_type}:keypoints"
            if key not in self.progress_manager.job_tracking:
                await self.progress_manager.initialize_with_high_expected(
                    job_id, asset_type, 0, event_type_prefix="keypoints"
                )
            await self.progress_manager.update_job_progress(
                job_id,
                asset_type,
                0,
                0,
                "keypoints",
            )

        key = f"{job_id}:{asset_type}:keypoints"
        if key in self.progress_manager.job_tracking:
            logger.info(
                "Checking for completion after batch initialization",
                job_id=job_id,
                asset_type=asset_type,
                total_items=total_items,
            )
            await self.progress_manager.update_expected_and_recheck_completion(
                job_id,
                asset_type,
                total_items,
                "keypoints",
            )
