from typing import Optional
from common_py.logging_config import configure_logging
from utils.deduper import Deduper
from vision_common import JobProgressManager
from utils.completion_manager import CompletionManager

logger = configure_logging("product-segmentor-service")

class AssetProcessor:
    def __init__(self, deduper: Deduper, image_masking_processor, db_updater, event_emitter, job_progress_manager: JobProgressManager, completion_manager: CompletionManager):
        self.deduper = deduper
        self.image_masking_processor = image_masking_processor
        self.db_updater = db_updater
        self.event_emitter = event_emitter
        self.job_progress_manager = job_progress_manager
        self.completion_manager = completion_manager

    async def handle_single_asset_processing(self, event_data: dict, asset_type: str, asset_id_key: str, db_update_func, emit_masked_func, job_id: str = "unknown") -> Optional[str]:
        """Generic handler for single asset processing (image or frame)."""
        asset_id = event_data[asset_id_key]
        local_path = event_data["local_path"]

        # Use deduplicator to prevent reprocessing
        asset_key = f"{job_id}:{asset_id}"
        if self.deduper.is_processed(asset_key):
            logger.info("Skipping duplicate asset", job_id=job_id, asset_id=asset_id, asset_type=asset_type)
            return None
        self.deduper.mark_processed(asset_key)

        logger.info("Processing item",
                   job_id=job_id,
                   asset_id=asset_id,
                   asset_type=asset_type,
                   item_path=local_path)

        mask_path = await self.image_masking_processor.process_single_image(
            image_id=asset_id,
            local_path=local_path,
            image_type=asset_type,
            job_id=job_id
        )

        if mask_path:
            # Update database
            await db_update_func(asset_id, mask_path)

            # Increment processed count and check for completion
            await self.job_progress_manager.update_job_progress(job_id, asset_type, 1, 1, "segmentation")
            current_processed = self.job_progress_manager.job_tracking[job_id]["done"]
            total_expected = self.job_progress_manager.job_tracking[job_id]["expected"]

            logger.debug("Progress update",
                        job_id=job_id,
                        asset_type=asset_type,
                        processed=current_processed,
                        total=total_expected)

            # Emit individual masked event if provided
            if emit_masked_func:
                await emit_masked_func(job_id=job_id, image_id=asset_id, mask_path=mask_path)

            # Check for batch completion - only complete if this asset matches the expected total
            if current_processed >= total_expected:
                logger.info("Batch completed",
                           job_id=job_id,
                           asset_type=asset_type,
                           processed=current_processed,
                           total=total_expected)
                await self.job_progress_manager._publish_completion_event(job_id, False, "segmentation")
                self.deduper.clear_all() # Clear deduplicator for this job

            logger.info("Item processed successfully",
                       job_id=job_id,
                       asset_id=asset_id,
                       asset_type=asset_type)
            return mask_path
        else:
            logger.error("Item processing failed",
                        job_id=job_id,
                        asset_id=asset_id,
                        asset_type=asset_type,
                        error="Mask generation failed")
            return None
