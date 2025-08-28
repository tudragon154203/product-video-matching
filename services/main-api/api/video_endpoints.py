import os
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from datetime import datetime, timezone
import pytz

from models.schemas import (
    VideoListResponse,
    FrameListResponse,
    VideoItem,
    FrameItem
)
from services.job.job_service import JobService
from common_py.crud.video_crud import VideoCRUD
from common_py.crud.video_frame_crud import VideoFrameCRUD
from common_py.database import DatabaseManager # Import DatabaseManager
from common_py.messaging import MessageBroker # Import MessageBroker
from api.dependency import get_db, get_broker
from config_loader import config
from utils.image_utils import to_public_url

router = APIRouter()

# Dependency functions use the centralized dependency module
def get_job_service(db: DatabaseManager = Depends(get_db), broker: MessageBroker = Depends(get_broker)) -> JobService:
    return JobService(db, broker)

def get_video_crud(db: DatabaseManager = Depends(get_db)) -> VideoCRUD:
    return VideoCRUD(db)

def get_video_frame_crud(db: DatabaseManager = Depends(get_db)) -> VideoFrameCRUD:
    return VideoFrameCRUD(db)


def get_gmt7_time(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert datetime to GMT+7 timezone"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(pytz.timezone('Asia/Saigon'))


@router.get("/jobs/{job_id}/videos", response_model=VideoListResponse)
async def get_job_videos(
    job_id: str,
    q: Optional[str] = Query(None, description="Search query for video titles"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    min_frames: Optional[int] = Query(None, description="Minimum number of frames"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    sort_by: str = Query("created_at", pattern="^(created_at|duration_s|frames_count|title)$", description="Field to sort by"),
    order: str = Query("DESC", pattern="^(ASC|DESC)$", description="Sort order"),
    job_service: JobService = Depends(get_job_service),
    video_crud: VideoCRUD = Depends(get_video_crud),
    video_frame_crud: VideoFrameCRUD = Depends(get_video_frame_crud)
):
    """
    Get videos for a specific job with filtering and pagination.
    
    Args:
        job_id: The job ID to filter videos by
        q: Search query for video titles (case-insensitive)
        platform: Filter by platform (e.g., 'youtube', 'tiktok')
        min_frames: Minimum number of frames a video must have
        limit: Maximum number of items to return (1-1000)
        offset: Number of items to skip for pagination
        sort_by: Field to sort by (updated_at, duration_s, frames_count, title)
        order: Sort order (ASC or DESC)
    
    Returns:
        VideoListResponse: Paginated list of videos matching the criteria
    """
    try:
        # Validate job exists
        job_status = await job_service.get_job_status(job_id)
        
        # If job_status.phase is "unknown", it means the job was not found in the database
        if job_status.phase == "unknown":
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        job = {"job_id": job_status.job_id, "updated_at": job_status.updated_at, "phase": job_status.phase, "percent": job_status.percent, "counts": job_status.counts}
        
        # Get videos with filtering and pagination
        videos = await video_crud.list_videos_by_job(
            job_id=job_id,
            search_query=q,
            platform=platform,
            min_frames=min_frames,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            order=order
        )
        
        # Get total count for pagination
        total = await video_crud.count_videos_by_job(
            job_id=job_id,
            search_query=q,
            platform=platform,
            min_frames=min_frames
        )
        
        # Convert to response format and ensure datetime is in GMT+7
        video_items = []
        for video in videos:
            frames_count = await video_frame_crud.get_video_frames_count(video.video_id)
            video_item = VideoItem(
                video_id=video.video_id,
                platform=video.platform,
                url=video.url,
                title=video.title or "",
                duration_s=float(video.duration_s or 0),
                frames_count=frames_count,
                updated_at=get_gmt7_time(video.created_at)
            )
            video_items.append(video_item)
        
        return VideoListResponse(
            items=video_items,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/jobs/{job_id}/videos/{video_id}/frames", response_model=FrameListResponse)
async def get_video_frames(
    job_id: str,
    video_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    sort_by: str = Query("ts", pattern="^(ts|frame_id)$", description="Field to sort by"),
    order: str = Query("ASC", pattern="^(ASC|DESC)$", description="Sort order"),
    job_service: JobService = Depends(get_job_service),
    video_crud: VideoCRUD = Depends(get_video_crud),
    video_frame_crud: VideoFrameCRUD = Depends(get_video_frame_crud)
):
    """
    Get frames for a specific video with pagination and sorting.
    
    Args:
        job_id: The job ID (used for validation)
        video_id: The video ID to get frames for
        limit: Maximum number of items to return (1-1000)
        offset: Number of items to skip for pagination
        sort_by: Field to sort by (ts, frame_id)
        order: Sort order (ASC or DESC)
    
    Returns:
        FrameListResponse: Paginated list of frames for the video
    """
    try:
        # Validate job exists
        job_status = await job_service.get_job_status(job_id)
        
        # If job_status.phase is "unknown", it means the job was not found in the database
        if job_status.phase == "unknown":
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        job = {"job_id": job_status.job_id, "updated_at": job_status.updated_at, "phase": job_status.phase, "percent": job_status.percent, "counts": job_status.counts}
        
        # Validate video exists and belongs to the job
        video = await video_crud.get_video(video_id)
        if not video:
            raise HTTPException(status_code=404, detail=f"Video {video_id} not found")
        
        if video.job_id != job_id:
            raise HTTPException(status_code=404, detail=f"Video {video_id} does not belong to job {job_id}")
        
        # Get frames with pagination and sorting
        frames = await video_frame_crud.list_video_frames_by_video(
            video_id=video_id,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            order=order
        )
        
        # Get total count for pagination
        total = await video_frame_crud.count_video_frames_by_video(video_id)
        
        # Convert to response format and ensure datetime is in GMT+7
        frame_items = []
        for frame in frames:
            # Generate public URL for the frame image
            public_url = to_public_url(frame.local_path, config.DATA_ROOT_CONTAINER)
            
            frame_item = FrameItem(
                frame_id=frame.frame_id,
                ts=frame.ts,
                local_path=frame.local_path,
                url=public_url,  # Add public URL field
                updated_at=get_gmt7_time(frame.created_at)
            )
            frame_items.append(frame_item)
        
        return FrameListResponse(
            items=frame_items,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")