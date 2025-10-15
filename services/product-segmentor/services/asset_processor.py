from typing import Optional
from common_py.logging_config import configure_logging
from vision_common import JobProgressManager
# CompletionManager was removed - using JobProgressManager directly

logger = configure_logging("product-segmentor:asset_processor")


class AssetProcessor:
    def __init__(self, image_masking_processor, db_updater, event_emitter, job_progress_manager: JobProgressManager):
        self.image_masking_processor = image_masking_processor
        self.db_updater = db_updater
        self.event_emitter = event_emitter
        self.job_progress_manager = job_progress_manager

    async def handle_single_asset_processing(
        self, event_data: dict, asset_type: str, asset_id_key: str,
        db_update_func, emit_masked_func, job_id: str = "unknown"
    ) -> Optional[str]:
        """Generic handler for single asset processing (image or frame)."""
        asset_id = event_data[asset_id_key]
        local_path = event_data["local_path"]

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

            # Increment processed count using main job progress manager to enable automatic completion
            await self.job_progress_manager.update_job_progress(job_id, asset_type, 0, 1, "segmentation")
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

            # Check for batch completion - this is now handled automatically by update_job_progress()
            # The update_job_progress() call above already triggers completion when done >= expected
            if current_processed >= total_expected:
                logger.info("Batch completion condition met (handled automatically by update_job_progress)",
                            job_id=job_id,
                            asset_type=asset_type,
                            processed=current_processed,
                            total=total_expected,
                            completion_trigger="automatic_from_update_job_progress")

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
