"""
Async streaming pipeline for parallel video search, download, and processing.

This module implements a streaming pipeline where search results are emitted as soon as
they're found, allowing downloads and processing to start in parallel with ongoing searches.
"""

import asyncio
from asyncio import Queue, Semaphore
from typing import Any, Dict, List, Optional, AsyncGenerator
from dataclasses import dataclass

from common_py.database import DatabaseManager
from common_py.logging_config import configure_logging
from config_loader import config
from services.idempotency_manager import IdempotencyManager
from fetcher.video_fetcher import VideoFetcher

logger = configure_logging("video-crawler:streaming_pipeline")


@dataclass
class VideoTask:
    """Represents a video processing task."""
    video_data: Dict[str, Any]
    job_id: str
    platform: str
    priority: int = 0  # Higher priority = processed first


@dataclass
class PipelineConfig:
    """Configuration for the streaming pipeline."""
    max_concurrent_downloads: int = 5
    max_concurrent_processing: int = 3
    download_queue_size: int = 100
    processing_queue_size: int = 50
    batch_size_for_processing: int = 10
    search_result_buffer_size: int = 20


class StreamingVideoPipeline:
    """
    Async streaming pipeline for parallel video processing.

    The pipeline consists of three main stages:
    1. Search → Results Stream (immediate emission)
    2. Download Queue → Parallel Downloads
    3. Processing Queue → Parallel Keyframe Extraction
    """

    def __init__(
        self,
        db: DatabaseManager,
        config: Optional[PipelineConfig] = None,
        idempotency_manager: Optional[IdempotencyManager] = None
    ):
        self.db = db
        self.config = config or PipelineConfig()
        self.idempotency_manager = idempotency_manager or IdempotencyManager(db)

        # Initialize queues and semaphores
        self.download_queue: Queue[VideoTask] = Queue(maxsize=self.config.download_queue_size)
        self.processing_queue: Queue[VideoTask] = Queue(maxsize=self.config.processing_queue_size)

        self.download_semaphore = Semaphore(self.config.max_concurrent_downloads)
        self.processing_semaphore = Semaphore(self.config.max_concurrent_processing)

        # Statistics and monitoring
        self.stats = {
            "search_results_found": 0,
            "downloads_started": 0,
            "downloads_completed": 0,
            "processing_started": 0,
            "processing_completed": 0,
            "duplicates_skipped": 0,
            "errors": 0
        }

        # Background tasks
        self.download_workers: List[asyncio.Task] = []
        self.processing_workers: List[asyncio.Task] = []
        self.is_running = False

    async def start_pipeline(self) -> None:
        """Start the background workers for the pipeline."""
        if self.is_running:
            return

        self.is_running = True

        # Start download workers
        for i in range(self.config.max_concurrent_downloads):
            worker = asyncio.create_task(
                self._download_worker(f"download_worker_{i}"),
                name=f"download_worker_{i}"
            )
            self.download_workers.append(worker)

        # Start processing workers
        for i in range(self.config.max_concurrent_processing):
            worker = asyncio.create_task(
                self._processing_worker(f"processing_worker_{i}"),
                name=f"processing_worker_{i}"
            )
            self.processing_workers.append(worker)

        logger.info(f"Started pipeline: {len(self.download_workers)} download workers, {len(self.processing_workers)} processing workers")

    async def stop_pipeline(self) -> None:
        """Stop the pipeline and cleanup workers."""
        if not self.is_running:
            return

        self.is_running = False

        # Cancel all workers
        all_workers = self.download_workers + self.processing_workers
        for worker in all_workers:
            worker.cancel()

        # Wait for workers to finish
        if all_workers:
            await asyncio.gather(*all_workers, return_exceptions=True)

        self.download_workers.clear()
        self.processing_workers.clear()

        logger.info("Pipeline stopped")

    async def process_videos_streaming(
        self,
        platform_queries: Dict[str, List[str]],
        job_id: str,
        progress_callback: Optional[callable] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process videos using streaming approach.

        Args:
            platform_queries: Dictionary mapping platforms to their search queries
            job_id: Job identifier for tracking
            progress_callback: Optional callback for progress updates

        Yields:
            Processing results as they complete
        """
        await self.start_pipeline()

        try:
            # Start parallel searches
            search_tasks = []
            for platform, queries in platform_queries.items():
                search_task = asyncio.create_task(
                    self._search_and_stream_results(platform, queries, job_id)
                )
                search_tasks.append(search_task)

            # Wait for all searches to complete
            await asyncio.gather(*search_tasks, return_exceptions=True)

            # Signal completion by putting sentinel values
            for _ in range(self.config.max_concurrent_downloads):
                await self.download_queue.put(None)  # Sentinel value

            # Wait for queues to be processed
            await self.download_queue.join()
            await self.processing_queue.join()

            # Final progress update
            if progress_callback:
                await progress_callback(self.stats)

            yield {"type": "pipeline_complete", "stats": self.stats}

        finally:
            await self.stop_pipeline()

    async def _search_and_stream_results(
        self,
        platform: str,
        queries: List[str],
        job_id: str
    ) -> None:
        """
        Search for videos and stream results immediately to download queue.

        This is the key innovation - results are queued as soon as found,
        not waiting for the entire search to complete.
        """
        try:
            video_fetcher = VideoFetcher(self.db)

            for query in queries:
                logger.info(f"Starting search for {platform}: {query}")

                # Get search results - this might need to be modified to support streaming
                # For now, we'll use the existing search but optimize the queuing
                search_results = await video_fetcher.fetch_videos(platform, [query])

                # Stream each result to download queue immediately
                for video_data in search_results:
                    task = VideoTask(
                        video_data=video_data,
                        job_id=job_id,
                        platform=platform,
                        priority=self._calculate_priority(video_data)
                    )

                    try:
                        await self.download_queue.put(task)
                        self.stats["search_results_found"] += 1

                        # Yield immediate result for monitoring
                        yield {"type": "video_queued", "video_id": video_data.get("video_id"), "platform": platform}

                    except asyncio.QueueFull:
                        logger.warning(f"Download queue full, dropping video: {video_data.get('video_id')}")
                        self.stats["errors"] += 1

        except Exception as e:
            logger.error(f"Error in search and stream for {platform}: {e}")
            self.stats["errors"] += 1

    async def _download_worker(self, worker_name: str) -> None:
        """Background worker that downloads videos from the queue."""
        logger.info(f"Started {worker_name}")

        while self.is_running:
            try:
                # Get task from queue with timeout
                task = await asyncio.wait_for(
                    self.download_queue.get(),
                    timeout=1.0
                )

                if task is None:  # Sentinel value
                    break

                async with self.download_semaphore:
                    await self._download_video(task)
                    self.download_queue.task_done()

            except asyncio.TimeoutError:
                continue  # Check if we should continue
            except Exception as e:
                logger.error(f"Error in {worker_name}: {e}")
                self.stats["errors"] += 1
                self.download_queue.task_done()

        logger.info(f"Stopped {worker_name}")

    async def _processing_worker(self, worker_name: str) -> None:
        """Background worker that processes downloaded videos."""
        logger.info(f"Started {worker_name}")

        while self.is_running:
            try:
                # Get task from queue with timeout
                task = await asyncio.wait_for(
                    self.processing_queue.get(),
                    timeout=1.0
                )

                if task is None:  # Sentinel value
                    break

                async with self.processing_semaphore:
                    await self._process_video(task)
                    self.processing_queue.task_done()

            except asyncio.TimeoutError:
                continue  # Check if we should continue
            except Exception as e:
                logger.error(f"Error in {worker_name}: {e}")
                self.stats["errors"] += 1
                self.processing_queue.task_done()

        logger.info(f"Stopped {worker_name}")

    async def _download_video(self, task: VideoTask) -> None:
        """Download a single video with idempotency checks."""
        try:
            self.stats["downloads_started"] += 1
            video_data = task.video_data
            video_id = video_data.get("video_id")
            platform = task.platform

            # Check if video already processed (idempotency)
            if await self.idempotency_manager.check_video_exists(video_id, platform):
                logger.info(f"Video already exists, skipping download: {video_id}")
                self.stats["duplicates_skipped"] += 1
                return

            # Check if file already exists locally
            existing_file = self._check_existing_file(video_data)
            if existing_file:
                video_data["local_path"] = existing_file
                logger.info(f"Video file already exists: {existing_file}")
            else:
                # Download the video (implement platform-specific download logic)
                downloaded_path = await self._download_video_file(video_data, platform)
                if downloaded_path:
                    video_data["local_path"] = downloaded_path
                else:
                    logger.warning(f"Failed to download video: {video_id}")
                    self.stats["errors"] += 1
                    return

            # Queue for processing
            await self.processing_queue.put(task)
            self.stats["downloads_completed"] += 1

        except Exception as e:
            logger.error(f"Error downloading video {task.video_data.get('video_id')}: {e}")
            self.stats["errors"] += 1

    async def _process_video(self, task: VideoTask) -> None:
        """Process a downloaded video (keyframe extraction) with idempotency."""
        try:
            self.stats["processing_started"] += 1
            video_data = task.video_data
            video_id = video_data.get("video_id")
            platform = task.platform

            # Create video record with idempotency
            created_new, actual_video_id = await self.idempotency_manager.create_video_with_idempotency(
                video_id=video_id,
                platform=platform,
                url=video_data.get("url"),
                title=video_data.get("title"),
                duration_s=video_data.get("duration_s"),
                job_id=task.job_id
            )

            if not created_new:
                logger.info(f"Video record already exists, skipping processing: {video_id}")
                self.stats["duplicates_skipped"] += 1
                return

            # Process keyframes (this would use the existing video processor)
            # For now, we'll create a placeholder
            frames_data = await self._extract_keyframes_with_idempotency(video_data, actual_video_id)

            self.stats["processing_completed"] += 1

            logger.info(f"Completed processing video: {actual_video_id}, frames: {len(frames_data)}")

        except Exception as e:
            logger.error(f"Error processing video {task.video_data.get('video_id')}: {e}")
            self.stats["errors"] += 1

    def _calculate_priority(self, video_data: Dict[str, Any]) -> int:
        """Calculate processing priority based on video characteristics."""
        # Simple priority based on duration - shorter videos get higher priority
        duration = video_data.get("duration_s", 0)
        if duration < 30:
            return 3  # High priority for short videos
        elif duration < 120:
            return 2  # Medium priority
        else:
            return 1  # Low priority for long videos

    def _check_existing_file(self, video_data: Dict[str, Any]) -> Optional[str]:
        """Check if video file already exists locally."""
        # This would integrate with existing file management logic
        # For now, return None to indicate no existing file
        return None

    async def _download_video_file(self, video_data: Dict[str, Any], platform: str) -> Optional[str]:
        """Download video file - platform-specific implementation."""
        # This would integrate with existing download logic
        # For now, return None as placeholder
        logger.info(f"Would download video: {video_data.get('video_id')} on {platform}")
        return None

    async def _extract_keyframes_with_idempotency(self, video_data: Dict[str, Any], video_id: str) -> List[Dict[str, Any]]:
        """Extract keyframes with idempotency checks."""
        # This would integrate with existing keyframe extraction logic
        # For now, return empty list as placeholder
        logger.info(f"Would extract keyframes for video: {video_id}")
        return []

    def get_stats(self) -> Dict[str, Any]:
        """Get current pipeline statistics."""
        return self.stats.copy()