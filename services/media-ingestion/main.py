import os
import asyncio
import uuid
import sys
sys.path.append('/app/libs')

from common_py.logging_config import configure_logging
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.crud import VideoCRUD, VideoFrameCRUD
from common_py.models import Video, VideoFrame
from contracts.validator import validator
from ingestion import VideoIngestion

# Configure logging
logger = configure_logging("media-ingestion")

# Environment variables
sys.path.append('/app/infra')
from config import config

POSTGRES_DSN = config.POSTGRES_DSN
BUS_BROKER = config.BUS_BROKER
DATA_ROOT = config.DATA_ROOT

# Global instances
db = DatabaseManager(POSTGRES_DSN)
broker = MessageBroker(BUS_BROKER)
video_crud = VideoCRUD(db)
frame_crud = VideoFrameCRUD(db)
ingestion = VideoIngestion(DATA_ROOT)


async def handle_videos_search_request(event_data):
    """Handle video search request"""
    try:
        # Validate event
        validator.validate_event("videos_search_request", event_data)
        
        job_id = event_data["job_id"]
        industry = event_data["industry"]
        queries = event_data["queries"]
        platforms = event_data["platforms"]
        recency_days = event_data["recency_days"]
        
        logger.info("Processing video search request", 
                   job_id=job_id, industry=industry, platforms=platforms)
        
        # Search videos on each platform
        all_videos = []
        
        for platform in platforms:
            if platform == "youtube":
                videos = await ingestion.search_youtube_videos(queries, recency_days)
                all_videos.extend(videos)
            elif platform == "bilibili":
                videos = await ingestion.search_bilibili_videos(queries, recency_days)
                all_videos.extend(videos)
        
        # Process each video
        for video_data in all_videos:
            await process_video(video_data, job_id)
        
        logger.info("Completed video search", 
                   job_id=job_id, 
                   total_videos=len(all_videos))
        
    except Exception as e:
        logger.error("Failed to process video search request", error=str(e))
        raise


async def process_video(video_data, job_id):
    """Process a single video and extract keyframes"""
    try:
        # Create video record
        video = Video(
            video_id=str(uuid.uuid4()),
            platform=video_data["platform"],
            url=video_data["url"],
            title=video_data["title"],
            duration_s=video_data.get("duration_s"),
            published_at=video_data.get("published_at")
        )
        
        # Save to database (need to add job_id)
        await db.execute(
            "INSERT INTO videos (video_id, platform, url, title, duration_s, published_at, job_id) VALUES ($1, $2, $3, $4, $5, $6, $7)",
            video.video_id, video.platform, video.url, 
            video.title, video.duration_s, video.published_at, job_id
        )
        
        # Download video and extract keyframes
        keyframes = await ingestion.extract_keyframes(video_data["url"], video.video_id)
        
        # Process each keyframe
        frame_data = []
        for i, (timestamp, frame_path) in enumerate(keyframes):
            frame_id = f"{video.video_id}_frame_{i}"
            
            # Create frame record
            frame = VideoFrame(
                frame_id=frame_id,
                video_id=video.video_id,
                ts=timestamp,
                local_path=frame_path
            )
            
            await frame_crud.create_video_frame(frame)
            
            frame_data.append({
                "frame_id": frame_id,
                "ts": timestamp,
                "local_path": frame_path
            })
        
        # Emit keyframes ready event
        if frame_data:
            await broker.publish_event(
                "videos.keyframes.ready",
                {
                    "video_id": video.video_id,
                    "frames": frame_data
                },
                correlation_id=job_id
            )
        
        logger.info("Processed video", video_id=video.video_id, 
                   frame_count=len(frame_data))
        
    except Exception as e:
        logger.error("Failed to process video", video_data=video_data, error=str(e))


async def main():
    """Main service loop"""
    try:
        # Initialize connections
        await db.connect()
        await broker.connect()
        
        # Subscribe to events
        await broker.subscribe_to_topic(
            "videos.search.request",
            handle_videos_search_request
        )
        
        logger.info("Media ingestion service started")
        
        # Keep service running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down media ingestion service")
    except Exception as e:
        logger.error("Service error", error=str(e))
    finally:
        await db.disconnect()
        await broker.disconnect()


if __name__ == "__main__":
    asyncio.run(main())