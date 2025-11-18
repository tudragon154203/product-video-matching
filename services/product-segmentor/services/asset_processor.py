import asyncio
from typing import Optional
from common_py.logging_config import configure_logging
from vision_common import JobProgressManager
from config_loader import config
from utils.gpu_memory_monitor import clear_gpu_memory

logger = configure_logging("product-segmentor:asset_processor")


class AssetProcessor:
    def __init__(self, image_masking_processor, db_updater, event_emitter, job_progress_manager: JobProgressManager):
        self.image_masking_processor = image_masking_processor
        self.db_updater = db_updater
        self.event_emitter = event_emitter
        self.job_progress_manager = job_progress_manager

    def _is_oom_error(self, error: Exception) -> bool:
        """Check if an exception is a CUDA OOM error.

        Args:
            error: Exception to check

        Returns:
            True if error is CUDA out-of-memory
        """
        error_str = str(error).lower()
        oom_indicators = [
            "cuda out of memory",
            "cudnn error: cudnn_status_alloc_failed",
            "out of memory",
            "cuda error",
        ]
        return any(indicator in error_str for indicator in oom_indicators)

    async def _process_with_retry(
        self,
        asset_id: str,
        local_path: str,
        asset_type: str,
        job_id: str,
    ) -> Optional[str]:
        """Process asset with OOM retry logic.

        Args:
            asset_id: Asset identifier
            local_path: Path to asset file
            asset_type: Type of asset (image/video)
            job_id: Job identifier

        Returns:
            Mask path if successful, None otherwise
        """
        max_retries = config.MAX_OOM_RETRIES if config.RETRY_ON_OOM else 0
        retry_delays = [0.5, 1.0, 2.0]  # Exponential backoff in seconds

        for attempt in range(max_retries + 1):
            try:
                mask_path = await self.image_masking_processor.process_single_image(
                    image_id=asset_id,
                    local_path=local_path,
                    image_type=asset_type,
                    job_id=job_id
                )
                return mask_path

            except Exception as e:
                is_oom = self._is_oom_error(e)

                if is_oom and attempt < max_retries:
                    # OOM error and we have retries left
                    delay = retry_delays[min(attempt, len(retry_delays) - 1)]

                    logger.warning(
                        "CUDA OOM detected, retrying after cleanup",
                        job_id=job_id,
                        asset_id=asset_id,
                        asset_type=asset_type,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        retry_delay=delay,
                        error=str(e),
                    )

                    # Force GPU memory cleanup
                    clear_gpu_memory()

                    # Wait before retry
                    await asyncio.sleep(delay)

                else:
                    # Either not OOM, or out of retries
                    if is_oom:
                        logger.error(
                            "CUDA OOM persists after all retries",
                            job_id=job_id,
                            asset_id=asset_id,
                            asset_type=asset_type,
                            attempts=attempt + 1,
                            error=str(e),
                        )
                    else:
                        logger.error(
                            "Asset processing failed (non-OOM error)",
                            job_id=job_id,
                            asset_id=asset_id,
                            asset_type=asset_type,
                            error=str(e),
                        )
                    return None

        return None

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

        # Process with OOM retry logic
        mask_path = await self._process_with_retry(
            asset_id=asset_id,
            local_path=local_path,
            asset_type=asset_type,
            job_id=job_id,
        )

        if mask_path:
            # Update database
            await db_update_func(asset_id, mask_path)

            # Increment processed count using segmentation prefix to enable automatic completion
            await self.job_progress_manager.update_job_progress(
                job_id, asset_type, 0, 1, event_type_prefix="segmentation"
            )
            key = f"{job_id}:{asset_type}:segmentation"
            current_processed = self.job_progress_manager.job_tracking[key]["done"]
            total_expected = self.job_progress_manager.job_tracking[key]["expected"]

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
            # Do NOT increment segmentation progress for failed items
            logger.error("Item processing failed",
                         job_id=job_id,
                         asset_id=asset_id,
                         asset_type=asset_type,
                         error="Mask generation failed")
            return None
