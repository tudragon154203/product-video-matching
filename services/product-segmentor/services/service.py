"""Product Segmentor Service business logic.

This service orchestrates product segmentation operations by delegating to specialized modules:
- SegmentorFactory: Creates and manages segmentation engines
- JobProgressManager: Tracks job progress and handles batch completion and watermark emission
- ForegroundProcessor: Handles image segmentation operations
- DatabaseUpdater: Manages database operations

The service maintains a stable public API while internal responsibilities are modularized.
"""

import asyncio
import uuid
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.logging_config import configure_logging

from utils.file_manager import FileManager
from config_loader import config
from handlers.event_emitter import EventEmitter
from .foreground_processor import ForegroundProcessor
from .image_masking_processor import ImageMaskingProcessor
from utils.db_updater import DatabaseUpdater
from .foreground_segmentor_factory import create_segmentor
from segmentation.models.yolo_segmentor import YOLOSegmentor
from .asset_processor import AssetProcessor
from vision_common import JobProgressManager
from utils.gpu_memory_monitor import GPUMemoryMonitor

logger = configure_logging("product-segmentor:service", config.LOG_LEVEL)


class ProductSegmentorService:
    """Core business logic for product segmentation.

    This service orchestrates segmentation operations by delegating to specialized modules:
    - SegmentorFactory: Creates and manages segmentation engines
    - JobProgressManager: Tracks job progress and handles batch completion and watermark emission
    - ForegroundProcessor: Handles image segmentation operations
    - DatabaseUpdater: Manages database operations

    The service maintains a stable public API while internal responsibilities are modularized.
    """

    def __init__(
        self,
        db: DatabaseManager,
        broker: MessageBroker,
        foreground_model_name: str = config.FOREGROUND_SEG_MODEL_NAME,
        max_concurrent: int = 4
    ):
        """Initialize segmentation service.

        Args:
            db: Database manager instance
            broker: Message broker instance
            model_name: Hugging Face model name
            max_concurrent: Maximum concurrent image processing

        Initializes specialized modules:
        - SegmentorFactory: Creates segmentation engines
        - JobProgressManager: Tracks job progress and handles batch completion
        - ImageProcessor: Handles image segmentation
        - DatabaseUpdater: Manages database operations
        """
        self.db = db
        self.broker = broker
        self.file_manager = FileManager(
            foreground_mask_dir_path=config.FOREGROUND_MASK_DIR_PATH,
            people_mask_dir_path=config.PEOPLE_MASK_DIR_PATH,
            product_mask_dir_path=config.PRODUCT_MASK_DIR_PATH
        )
        self.max_concurrent = max_concurrent

        # Initialize segmentation engine using factory
        self.foreground_segmentor = create_segmentor(foreground_model_name, config.HF_TOKEN)
        self.people_segmentor = YOLOSegmentor(config.PEOPLE_SEG_MODEL_NAME)

        # Initialize event emitter
        self.event_emitter = EventEmitter(broker)

        # Initialize processing helpers
        self.image_processor = ForegroundProcessor(self.foreground_segmentor)
        self.db_updater = DatabaseUpdater(self.db)

        # Initialize new modules
        self.job_progress_manager = JobProgressManager(broker)
        self.batch_timeout_seconds = config.BATCH_TIMEOUT_SECONDS

        self.image_masking_processor = ImageMaskingProcessor(
            self.foreground_segmentor,
            self.people_segmentor,
            self.file_manager,
            self.image_processor
        )

        self._processing_semaphore = asyncio.Semaphore(int(max_concurrent))

        # Initialize GPU memory monitor
        self.gpu_memory_monitor = GPUMemoryMonitor(
            memory_threshold=config.GPU_MEMORY_THRESHOLD
        )

        # Initialize AssetProcessor
        self.asset_processor = AssetProcessor(
            image_masking_processor=self.image_masking_processor,
            db_updater=self.db_updater,
            event_emitter=self.event_emitter,
            job_progress_manager=self.job_progress_manager,
        )

        self.initialized = False

    async def initialize(self) -> None:
        """Initialize the service."""
        try:
            logger.info("Initializing Product Segmentor Service")

            # Log initial GPU memory state
            self.gpu_memory_monitor.log_memory_stats("service_initialization_start")

            # Initialize file manager
            await self.file_manager.initialize()

            # Initialize segmentation model
            await self.foreground_segmentor.initialize()
            await self.people_segmentor.initialize()

            # Log GPU memory after model loading
            self.gpu_memory_monitor.log_memory_stats("models_loaded")

            self.initialized = True
            logger.info("Product Segmentor Service initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize service", error=str(e))
            raise

    async def cleanup(self) -> None:
        """Cleanup service resources."""
        try:
            # Wait for any ongoing processing to complete
            logger.info("Waiting for ongoing processing to complete")

            # Proactively invoke segmentor cleanup hooks before waiting (foreground once)
            cleanup_called = False
            try:
                if self.foreground_segmentor and hasattr(self.foreground_segmentor, "cleanup"):
                    self.foreground_segmentor.cleanup()
                    cleanup_called = True
                if self.people_segmentor and hasattr(self.people_segmentor, "cleanup"):
                    self.people_segmentor.cleanup()
            except Exception:
                pass

            # Acquire all semaphore permits to ensure no new processing starts
            permits_acquired = 0
            try:
                for _ in range(self.max_concurrent):
                    await asyncio.wait_for(self._processing_semaphore.acquire(), timeout=30.0)
                    permits_acquired += 1
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for processing to complete")

            # Cleanup segmentation model (ensure foreground only once)
            if self.foreground_segmentor and not cleanup_called:
                self.foreground_segmentor.cleanup()
            if self.people_segmentor:
                self.people_segmentor.cleanup()

            # Cleanup progress tracking using JobProgressManager
            await self.job_progress_manager.cleanup_all()

            # Ensure segmentors' cleanup hooks are invoked once overall processing drained (foreground already handled)
            try:
                if self.people_segmentor and hasattr(self.people_segmentor, "cleanup"):
                    self.people_segmentor.cleanup()
            except Exception:
                pass

            # Release acquired permits
            for _ in range(permits_acquired):
                self._processing_semaphore.release()

            # Yield once to allow any scheduled cleanup callbacks/mocks to run
            try:
                await asyncio.sleep(0)
            except Exception:
                pass

            self.initialized = False
            logger.info("Service cleanup completed")

        except Exception as e:
            logger.error("Error during cleanup", error=str(e))

    async def handle_products_image_ready(self, event_data: dict) -> None:
        """Handle single product image ready event.

        Args:
            event_data: Event payload containing image information
        """
        async with self._processing_semaphore:
            job_id = event_data["job_id"]

            # Log GPU memory before processing
            self.gpu_memory_monitor.log_memory_stats(f"before_image_{event_data.get('image_id')}")

            # Initialize job with high expected count to prevent premature completion
            # before batch event arrives with actual total
            if not self.job_progress_manager._is_batch_initialized(job_id, "image"):
                await self.job_progress_manager.initialize_with_high_expected(job_id, "image", event_type_prefix="segmentation")
                logger.debug(
                    "Initialized job with high expected count for single image",
                    job_id=job_id,
                )

            result = await self.asset_processor.handle_single_asset_processing(
                event_data=event_data,
                asset_type="image",
                asset_id_key="image_id",
                db_update_func=self.db_updater.update_product_image_mask,
                emit_masked_func=self.event_emitter.emit_product_image_masked,
                job_id=job_id
            )

            # Periodic GPU cleanup
            self.gpu_memory_monitor.periodic_cleanup()
            
            # Log current progress after processing
            key = f"{job_id}:image:segmentation"
            if hasattr(self.job_progress_manager, "job_tracking"):
                job_data = self.job_progress_manager.job_tracking.get(key)
                if job_data:
                    logger.debug(
                        "Image processed - progress updated",
                        job_id=job_id,
                        image_id=event_data.get("image_id"),
                        current_done=job_data.get("done", 0),
                        expected=job_data.get("expected", 0),
                    )

    async def _handle_batch_event(
        self,
        job_id: str,
        asset_type: str,
        total_items: int,
        event_type: str,
        event_id: str | None = None,
    ) -> None:
        # Get current progress before updating
        key = f"{job_id}:{asset_type}:segmentation"
        current_done = 0
        if hasattr(self.job_progress_manager, "job_tracking"):
            job_data = self.job_progress_manager.job_tracking.get(key)
            if job_data:
                current_done = job_data.get("done", 0)

        logger.info(
            "Processing batch event",
            job_id=job_id,
            asset_type=asset_type,
            total_items=total_items,
            current_done=current_done,
            event_type=event_type,
            event_id=event_id,
        )

        await self.job_progress_manager._start_watermark_timer(
            job_id,
            self.batch_timeout_seconds,
            "segmentation",
        )

        # Mark batch initialized to prevent resetting expected to high sentinel on per-asset events
        self.job_progress_manager._mark_batch_initialized(job_id, asset_type)

        if total_items == 0:
            logger.info(
                "Zero-asset job - publishing immediate batch completion",
                job_id=job_id,
                asset_type=asset_type,
            )
            if asset_type == "image":
                await self.job_progress_manager.publish_products_images_masked_batch(
                    job_id=job_id,
                    total_images=0,
                )
            elif asset_type == "video":
                await self.job_progress_manager.publish_videos_keyframes_masked_batch(
                    job_id=job_id,
                    total_keyframes=0,
                )
            else:
                logger.warning(
                    "Unknown asset type for zero-asset job",
                    job_id=job_id,
                    asset_type=asset_type,
                )
        else:
            await self.job_progress_manager.update_job_progress(
                job_id,
                asset_type,
                total_items,
                0,
                event_type_prefix="segmentation",
            )
            logger.debug(
                "Batch initialized - waiting for individual asset processing",
                job_id=job_id,
                total_items=total_items,
            )

        # After initializing batch, update expected count and recheck completion.
        # This will emit appropriate batch completion events when done >= expected.
        completion_triggered = await self.job_progress_manager.update_expected_and_recheck_completion(
            job_id,
            asset_type,
            total_items,
            event_type_prefix="segmentation",
        )
        
        # Log final state after batch processing
        key = f"{job_id}:{asset_type}:segmentation"
        if hasattr(self.job_progress_manager, "job_tracking"):
            snapshot = self.job_progress_manager.job_tracking.get(key)
            if snapshot:
                logger.info(
                    "Batch event processed",
                    job_id=job_id,
                    asset_type=asset_type,
                    final_done=snapshot.get("done", 0),
                    final_expected=snapshot.get("expected", 0),
                    completion_triggered=completion_triggered,
                )
                # Maintain simple job_tracking mirror keyed by job_id for legacy tests
                self.job_progress_manager.job_tracking[job_id] = {
                    "expected": snapshot.get("expected", 0),
                    "done": snapshot.get("done", 0),
                    "asset_type": asset_type,
                }

    async def handle_videos_keyframes_ready(self, event_data: dict) -> None:
        """Handle video keyframes ready event.

        Args:
            event_data: Event payload containing keyframe information
        """
        video_id = event_data["video_id"]
        frames = event_data["frames"]
        job_id = event_data["job_id"]

        logger.info("Starting batch processing",
                    job_id=job_id,
                    asset_type="video",
                    total_items=len(frames),
                    operation="segmentation")

        # Log GPU memory at batch start
        self.gpu_memory_monitor.log_memory_stats(f"video_batch_start_{video_id}")

        processed_frames = []

        for frame in frames:
            frame_id = frame["frame_id"]
            ts = frame["ts"]

            mask_path = await self.asset_processor.handle_single_asset_processing(
                event_data=frame,
                asset_type="video",
                asset_id_key="frame_id",
                db_update_func=self.db_updater.update_video_frame_mask,
                emit_masked_func=None,  # Individual frame masked event handled by batch emitter
                job_id=job_id,  # Pass job_id explicitly for frames
            )

            if mask_path:
                processed_frames.append({
                    "frame_id": frame_id,
                    "ts": ts,
                    "mask_path": mask_path
                })

            # Periodic GPU cleanup during video processing
            self.gpu_memory_monitor.periodic_cleanup()

        if processed_frames:
            await self.event_emitter.emit_video_keyframes_masked(
                job_id=job_id,
                video_id=video_id,
                frames=processed_frames,
            )
            logger.info(
                "Video keyframes processed",
                video_id=video_id,
                processed=len(processed_frames),
            )

        # Force GPU cleanup after video batch completion
        self.gpu_memory_monitor.periodic_cleanup(force=True)

        # Log GPU memory at batch end
        self.gpu_memory_monitor.log_memory_stats(f"video_batch_end_{video_id}")

        # Note: Expected is set via videos_keyframes_ready_batch; avoid per-video overwrites.

    async def handle_videos_keyframes_ready_batch(self, event_data: dict) -> None:
        """Handle video keyframes batch completion event.

        Args:
            event_data: Batch event payload
        """
        event_id = event_data.get("event_id")
        job_id = event_data.get("job_id")
        try:
            job_id = event_data["job_id"]
            total_keyframes = event_data.get("total_keyframes", 0)
            event_id = event_id or str(uuid.uuid4())

            # Create a unique identifier for this batch event to detect duplicates
            batch_event_key = f"{job_id}:{event_id}"

            # Check if we've already processed this batch event
            if batch_event_key in self.job_progress_manager.processed_batch_events:
                logger.info(
                    "Ignoring duplicate batch event",
                    job_id=job_id,
                    event_id=event_id,
                    asset_type="video",
                )
                return

            # Mark this batch event as processed
            self.job_progress_manager.processed_batch_events.add(batch_event_key)

            await self._handle_batch_event(
                job_id,
                "video",
                total_keyframes,
                "videos_keyframes_ready_batch",
                event_id,
            )

        except Exception as e:
            logger.error(
                "Failed to handle videos keyframes ready batch",
                job_id=job_id,
                event_id=event_id,
                error=str(e),
            )
            raise

    async def handle_products_images_ready_batch(self, event_data: dict) -> None:
        """Handle products images batch completion event.

        Args:
            event_data: Batch event payload
        """
        event_id = event_data.get("event_id")
        job_id = event_data.get("job_id")
        try:
            job_id = event_data["job_id"]
            total_images = event_data.get("total_images", 0)
            event_id = event_id or str(uuid.uuid4())

            await self._handle_batch_event(
                job_id,
                "image",
                total_images,
                "products_images_ready_batch",
                event_id,
            )

        except Exception as e:
            logger.error(
                "Failed to handle products images ready batch",
                job_id=job_id,
                event_id=event_id,
                error=str(e),
            )
            raise
