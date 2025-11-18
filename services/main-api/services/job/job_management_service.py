import uuid
from fastapi import HTTPException
from common_py.logging_config import configure_logging
from models.schemas import StartJobRequest, StartJobResponse, JobStatusResponse
from services.llm.llm_service import LLMService
from services.llm.prompt_service import PromptService
from handlers.database_handler import DatabaseHandler
from handlers.broker_handler import BrokerHandler
from .job_initializer import JobInitializer

logger = configure_logging("main-api:job_management_service")


class JobManagementService:
    def __init__(self, db_handler: DatabaseHandler, broker_handler: BrokerHandler):
        self.db_handler = db_handler
        self.broker_handler = broker_handler
        self.llm_service = LLMService()
        self.prompt_service = PromptService()
        self.job_initializer = JobInitializer(
            db_handler, broker_handler, self.llm_service, self.prompt_service)

    async def start_job(self, request: StartJobRequest) -> StartJobResponse:
        try:
            job_id = str(uuid.uuid4())

            await self.job_initializer.initialize_job(job_id, request)

            logger.info(f"Started job (job_id: {job_id})")
            return StartJobResponse(job_id=job_id, status="started")

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e) if str(e) else 'Unknown error'}"
            logger.error(
                f"Failed to start job: {error_msg} (exception_type: {type(e).__name__})")
            import traceback
            logger.error(f"Exception traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=error_msg)

    async def get_job(self, job_id: str):
        """Get a complete job record by ID."""
        try:
            logger.debug(f"Attempting to get job for job_id: {job_id}")
            job = await self.db_handler.get_job(job_id)
            logger.debug(f"Result of db_handler.get_job for {job_id}: {job}")

            if not job:
                return None

            return job
        except Exception as e:
            logger.error(
                f"Failed to get job (job_id: {job_id}, error: {str(e)})")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_job_status(self, job_id: str) -> JobStatusResponse:
        try:
            logger.debug(f"Attempting to get job status for job_id: {job_id}")
            job = await self.db_handler.get_job(job_id)
            logger.debug(f"Result of db_handler.get_job for {job_id}: {job}")

            if not job:
                return JobStatusResponse(
                    job_id=job_id,
                    phase="unknown",
                    percent=0.0,
                    counts={
                        "products": 0,
                        "videos": 0,
                        "images": 0,
                        "frames": 0
                    },
                    collection={
                        "products_done": False,
                        "videos_done": False,
                    },
                    updated_at=None
                )

            phase_progress = {
                "collection": 20.0,
                "feature_extraction": 50.0,
                "matching": 80.0,
                "evidence": 90.0,
                "completed": 100.0,
                "failed": 0.0
            }

            # Get comprehensive counts including frames
            counts = await self.db_handler.get_job_counts_with_frames(job_id)
            product_count, video_count, image_count, frame_count, match_count = counts
            updated_at = await self.db_handler.get_job_updated_at(job_id)

            # Determine collection completion flags based on phase_events
            try:
                products_collection_done = await self.db_handler.has_phase_event(
                    job_id, "products.collections.completed"
                )
            except Exception:
                products_collection_done = False
            try:
                videos_collection_done = await self.db_handler.has_phase_event(job_id, "videos.collections.completed")
            except Exception:
                videos_collection_done = False

            return JobStatusResponse(
                job_id=job_id,
                phase=job["phase"],
                percent=phase_progress.get(job["phase"], 0.0),
                counts={
                    "products": product_count,
                    "videos": video_count,
                    "images": image_count,
                    "frames": frame_count
                },
                collection={
                    "products_done": bool(products_collection_done),
                    "videos_done": bool(videos_collection_done),
                },
                updated_at=updated_at
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Failed to get job status (job_id: {job_id}, error: {str(e)})")
            raise HTTPException(status_code=500, detail=str(e))

    async def list_jobs(self, limit: int = 50, offset: int = 0, status: str = None):
        """List jobs with pagination and optional status filtering.

        Args:
            limit: Maximum number of jobs to return (default: 50)
            offset: Number of jobs to skip for pagination (default: 0)
            status: Filter by job phase/status (e.g., 'completed', 'failed', 'in_progress')

        Returns:
            tuple: (list of jobs, total count)
        """
        try:
            return await self.db_handler.list_jobs(limit, offset, status)
        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def cancel_job(self, job_id: str, reason: str = "user_request", notes: str = None, cancelled_by: str = None):
        """Cancel a job and purge its messages from RabbitMQ.

        Args:
            job_id: The job ID to cancel
            reason: Reason for cancellation
            notes: Optional notes
            cancelled_by: Operator/user who requested cancellation

        Returns:
            dict with cancellation details
        """
        try:
            # Check if job exists
            job = await self.db_handler.get_job(job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")

            # If already cancelled, return existing cancellation info (idempotent)
            if job["phase"] == "cancelled":
                cancel_info = await self.db_handler.get_job_cancellation_info(job_id)
                if cancel_info:
                    return {
                        "job_id": job_id,
                        "phase": "cancelled",
                        "cancelled_at": cancel_info["cancelled_at"],
                        "reason": cancel_info["reason"],
                        "notes": cancel_info.get("notes")
                    }

            # If already completed/failed, return current state
            if job["phase"] in ("completed", "failed"):
                logger.info(f"Job {job_id} already in terminal state: {job['phase']}")
                return {
                    "job_id": job_id,
                    "phase": job["phase"],
                    "cancelled_at": None,
                    "reason": f"Job already {job['phase']}",
                    "notes": "Cannot cancel completed or failed jobs"
                }

            # Update database to mark as cancelled
            await self.db_handler.cancel_job(job_id, reason, notes, cancelled_by)

            # Purge RabbitMQ messages for this job
            try:
                purged_count = await self.broker_handler.purge_job_messages(job_id)
                logger.info(f"Purged {purged_count} messages for job {job_id}")
            except Exception as e:
                logger.warning(f"Failed to purge messages for job {job_id}: {e}")

            # Publish cancellation event to notify workers
            await self.broker_handler.publish_job_cancelled(job_id, reason, cancelled_by)

            # Get updated cancellation info
            cancel_info = await self.db_handler.get_job_cancellation_info(job_id)

            return {
                "job_id": job_id,
                "phase": "cancelled",
                "cancelled_at": cancel_info["cancelled_at"],
                "reason": cancel_info["reason"],
                "notes": cancel_info.get("notes")
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def delete_job(self, job_id: str, force: bool = False, deleted_by: str = None):
        """Delete a job and all its associated data.

        Args:
            job_id: The job ID to delete
            force: If True, skip waiting for cancellation on active jobs
            deleted_by: Operator/user who requested deletion

        Returns:
            dict with deletion details
        """
        try:
            # Check if job exists
            job = await self.db_handler.get_job(job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")

            # Check if already deleted
            if job.get("deleted_at"):
                logger.info(f"Job {job_id} already deleted")
                return {
                    "job_id": job_id,
                    "status": "deleted",
                    "deleted_at": job["deleted_at"]
                }

            # If job is active and force is not set, require cancellation first
            is_active = await self.db_handler.is_job_active(job_id)
            if is_active and not force:
                raise HTTPException(
                    status_code=409,
                    detail="Job is still active. Cancel it first or use force=true"
                )

            # If active, cancel first
            if is_active:
                logger.info(f"Cancelling active job {job_id} before deletion")
                await self.cancel_job(job_id, reason="deletion_requested", cancelled_by=deleted_by)

            # Delete all job data from database
            await self.db_handler.delete_job_data(job_id, deleted_by)

            # Publish deletion event
            await self.broker_handler.publish_job_deleted(job_id)

            # Get updated job info
            job = await self.db_handler.get_job(job_id)

            return {
                "job_id": job_id,
                "status": "deleted",
                "deleted_at": job["deleted_at"]
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete job {job_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
