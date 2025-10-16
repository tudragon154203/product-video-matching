"""
Parallel video processing service that integrates the streaming pipeline with existing components.

This service provides a drop-in replacement for the existing sequential video processing,
offering significant performance improvements through parallelization while maintaining
full idempotency and backward compatibility.
"""

from typing import Any, Dict, List, Optional, AsyncGenerator
import asyncio

from common_py.database import DatabaseManager
from common_py.logging_config import configure_logging
from handlers.event_emitter import EventEmitter
from services.idempotency_manager import IdempotencyManager
from services.streaming_pipeline import StreamingVideoPipeline, PipelineConfig
from services.video_processor import VideoProcessor
from vision_common import JobProgressManager

logger = configure_logging("video-crawler:parallel_video_service")


class ParallelVideoService:
    """
    High-level service for parallel video processing.

    This service combines:
    - Streaming pipeline for parallel search/download/processing
    - Enhanced video processor with idempotency
    - Event emission for downstream services
    - Progress tracking and monitoring
    """

    def __init__(
        self,
        db: DatabaseManager,
        event_emitter: Optional[EventEmitter] = None,
        job_progress_manager: Optional[JobProgressManager] = None,
        config: Optional[PipelineConfig] = None
    ):
        self.db = db
        self.event_emitter = event_emitter
        self.job_progress_manager = job_progress_manager
        self.config = config or PipelineConfig()

        # Job context for progress updates
        self._current_job_id: Optional[str] = None

        # Initialize components
        self.idempotency_manager = IdempotencyManager(db)
        self.video_processor = VideoProcessor(
            db=db,
            event_emitter=event_emitter,
            job_progress_manager=job_progress_manager,
            idempotency_manager=self.idempotency_manager
        )
        self.pipeline = StreamingVideoPipeline(
            db=db,
            config=config,
            idempotency_manager=self.idempotency_manager
        )

    async def process_videos_parallel(
        self,
        platform_queries: Dict[str, List[str]],
        job_id: str,
        use_streaming: bool = True
    ) -> Dict[str, Any]:
        """
        Process videos using parallel approach.

        Args:
            platform_queries: Dictionary mapping platforms to search queries
            job_id: Job identifier for tracking
            use_streaming: Whether to use streaming approach (recommended)

        Returns:
            Processing results with statistics
        """
        if use_streaming:
            return await self._process_videos_streaming(platform_queries, job_id)
        else:
            return await self._process_videos_batch(platform_queries, job_id)

    async def _process_videos_streaming(
        self,
        platform_queries: Dict[str, List[str]],
        job_id: str
    ) -> Dict[str, Any]:
        """Process videos using streaming pipeline for maximum parallelism."""
        logger.info(f"Starting streaming parallel processing for job {job_id}")

        results = []
        total_processed = 0
        total_skipped = 0
        total_errors = 0

        # Set job context for progress updates
        self._current_job_id = job_id

        try:
            async for result in self.pipeline.process_videos_streaming(
                platform_queries=platform_queries,
                job_id=job_id,
                progress_callback=self._update_progress_callback
            ):
                results.append(result)

                if result.get("type") == "pipeline_complete":
                    stats = result.get("stats", {})
                    total_processed = stats.get("processing_completed", 0)
                    total_skipped = stats.get("duplicates_skipped", 0)
                    total_errors = stats.get("errors", 0)

        except Exception as e:
            logger.error(f"Error in streaming processing: {e}")
            total_errors += 1
        finally:
            # Clear job context
            self._current_job_id = None

        final_stats = self.pipeline.get_stats()

        logger.info(
            f"Completed streaming processing for job {job_id}: "
            f"processed={total_processed}, skipped={total_skipped}, errors={total_errors}"
        )

        return {
            "job_id": job_id,
            "processing_type": "streaming_parallel",
            "stats": final_stats,
            "results": results,
            "summary": {
                "total_processed": total_processed,
                "total_skipped": total_skipped,
                "total_errors": total_errors,
                "success_rate": (total_processed / max(1, total_processed + total_errors)) * 100
            }
        }

    async def _process_videos_batch(
        self,
        platform_queries: Dict[str, List[str]],
        job_id: str
    ) -> Dict[str, Any]:
        """Process videos using batch parallel processing (fallback)."""
        logger.info(f"Starting batch parallel processing for job {job_id}")

        # This would implement batch parallel processing as a fallback
        # For now, we'll use the existing sequential logic but parallelized per platform
        from fetcher.video_fetcher import VideoFetcher

        video_fetcher = VideoFetcher(self.db)
        all_videos = []
        total_processed = 0
        total_skipped = 0
        total_errors = 0

        try:
            # Fetch all videos from all platforms in parallel
            platform_tasks = []
            for platform, queries in platform_queries.items():
                task = asyncio.create_task(
                    video_fetcher.fetch_videos(platform, queries)
                )
                platform_tasks.append((platform, task))

            # Collect all results
            for platform, task in platform_tasks:
                try:
                    videos = await task
                    all_videos.extend(videos)
                except Exception as e:
                    logger.error(f"Error fetching videos from {platform}: {e}")
                    total_errors += 1

            # Integration workload throttling: apply env-driven slice once per job
            try:
                import os  # local import to avoid top-level changes
                enforce_real = os.getenv("INTEGRATION_TESTS_ENFORCE_REAL_SERVICES", "").lower() == "true"
                max_videos_env = os.getenv("PVM_MAX_VIDEOS_FOR_IT")
                if enforce_real and max_videos_env:
                    max_videos = int(max_videos_env)
                    if max_videos > 0 and isinstance(all_videos, list):
                        if len(all_videos) > max_videos:
                            all_videos = all_videos[:max_videos]
                        logger.info(f"Integration max videos applied: {max_videos} for job_id {job_id}")
            except Exception as e:
                logger.warning(f"Failed to apply integration workload limit in ParallelVideoService: {e}")

            # Process videos in parallel batches
            semaphore = asyncio.Semaphore(self.config.max_concurrent_processing)

            async def process_single_video(video_data: Dict[str, Any]) -> Dict[str, Any]:
                async with semaphore:
                    try:
                        result = await self.video_processor.process_video(video_data, job_id)
                        if result.get("skipped"):
                            nonlocal total_skipped
                            total_skipped += 1
                        elif result.get("video_id"):
                            nonlocal total_processed
                            total_processed += 1
                        return result
                    except Exception as e:
                        nonlocal total_errors
                        total_errors += 1
                        logger.error(f"Error processing video: {e}")
                        return {"video_id": None, "error": str(e)}

            # Process all videos in parallel
            processing_tasks = [
                process_single_video(video_data) for video_data in all_videos
            ]

            results = await asyncio.gather(*processing_tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            total_errors += 1

        logger.info(
            f"Completed batch processing for job {job_id}: "
            f"processed={total_processed}, skipped={total_skipped}, errors={total_errors}"
        )

        return {
            "job_id": job_id,
            "processing_type": "batch_parallel",
            "stats": {
                "total_videos_found": len(all_videos),
                "processing_completed": total_processed,
                "duplicates_skipped": total_skipped,
                "errors": total_errors
            },
            "results": results,
            "summary": {
                "total_processed": total_processed,
                "total_skipped": total_skipped,
                "total_errors": total_errors,
                "success_rate": (total_processed / max(1, total_processed + total_errors)) * 100
            }
        }

    async def _update_progress_callback(self, stats: Dict[str, Any]) -> None:
        """Callback for progress updates during processing."""
        if self.job_progress_manager:
            # Update job progress based on current statistics
            total_started = stats.get("processing_started", 0)
            total_completed = stats.get("processing_completed", 0)

            if total_started > 0:
                progress_percentage = (total_completed / total_started) * 100

                await self.job_progress_manager.update_job_progress(
                    job_id=self._current_job_id or stats.get("job_id", ""),
                    item_type="video",
                    completed=total_completed,
                    total=total_started,
                    phase="processing"
                )

    async def get_processing_stats(self, job_id: Optional[str] = None) -> Dict[str, Any]:
        """Get current processing statistics."""
        pipeline_stats = self.pipeline.get_stats()

        if job_id:
            # Add job-specific statistics from database
            try:
                video_count = await self.db.fetch_one(
                    "SELECT COUNT(*) as count FROM videos WHERE job_id = $1",
                    job_id
                )
                frame_count = await self.db.fetch_one(
                    "SELECT COUNT(*) as count FROM video_frames vf JOIN videos v ON vf.video_id = v.video_id WHERE v.job_id = $1",
                    job_id
                )

                pipeline_stats.update({
                    "job_video_count": video_count["count"] if video_count else 0,
                    "job_frame_count": frame_count["count"] if frame_count else 0
                })
            except Exception as e:
                logger.error(f"Error fetching job stats: {e}")

        return pipeline_stats

    async def cleanup_resources(self) -> None:
        """Cleanup resources and stop background workers."""
        await self.pipeline.stop_pipeline()
        logger.info("Parallel video service cleaned up")
