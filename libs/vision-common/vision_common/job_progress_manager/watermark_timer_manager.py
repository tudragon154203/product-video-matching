import asyncio
from typing import Dict, Any, Set, Optional
from common_py.logging_config import configure_logging

logger = configure_logging("vision-common:watermark_timer_manager")

class WatermarkTimerManager:
    def __init__(self, completion_publisher):
        self.watermark_timers: Dict[str, asyncio.Task] = {}  # Watermark timers for jobs
        self.completion_publisher = completion_publisher

    async def start_watermark_timer(self, job_id: str, ttl: int = 300, event_type_prefix: str = "embeddings"):
        """Start a watermark timer for a job"""
        if job_id in self.watermark_timers:
            self.watermark_timers[job_id].cancel()
        
        async def timer_task():
            await asyncio.sleep(ttl)
            await self.completion_publisher.publish_completion_event(job_id, is_timeout=True, event_type_prefix=event_type_prefix)
            if job_id in self.watermark_timers:
                del self.watermark_timers[job_id]
        
        self.watermark_timers[job_id] = asyncio.create_task(timer_task())

    def cancel_watermark_timer(self, job_id: str):
        """Cancel the watermark timer for a job"""
        if job_id in self.watermark_timers:
            self.watermark_timers[job_id].cancel()
            del self.watermark_timers[job_id]

    async def cleanup_all(self):
        """Clean up all resources (for service shutdown)"""
        # Cancel all watermark timers
        for timer in self.watermark_timers.values():
            timer.cancel()
        self.watermark_timers.clear()
