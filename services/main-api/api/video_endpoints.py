from fastapi import APIRouter, HTTPException, Query
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

router = APIRouter()

# Global instances (will be set in main.py)
db_instance = None
job_service_instance = None
video_crud_instance = None
video_frame_crud_instance = None


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
    sort_by: str = Query("updated_at", pattern="^(updated_at|duration_s|frames_count|title)$", description="Field to sort by"),
    order: str = Query("DESC", pattern="^(ASC|DESC)$", description="Sort order")
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
        job = await job_service_instance.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # Get videos with filtering and pagination
        videos = await video_crud_instance.list_videos_by_job(
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
        total = await video_crud_instance.count_videos_by_job(
            job_id=job_id,
            search_query=q,
            platform=platform,
            min_frames=min_frames
        )
        
        # Convert to response format and ensure datetime is in GMT+7
        video_items = []
        for video in videos:
            frames_count = await video_crud_instance.get_video_frames_count(video.video_id)
            video_item = VideoItem(
                video_id=video.video_id,
                platform=video.platform,
                url=video.url,
                title=video.title or "",
                duration_s=float(video.duration_s or 0),
                frames_count=frames_count,
                updated_at=get_gmt7_time(video.updated_at or video.created_at)
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
    order: str = Query("ASC", pattern="^(ASC|DESC)$", description="Sort order")
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
        job = await job_service_instance.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # Validate video exists and belongs to the job
        video = await video_crud_instance.get_video(video_id)
        if not video:
            raise HTTPException(status_code=404, detail=f"Video {video_id} not found")
        
        if video.job_id != job_id:
            raise HTTPException(status_code=404, detail=f"Video {video_id} does not belong to job {job_id}")
        
        # Get frames with pagination and sorting
        frames = await video_frame_crud_instance.list_video_frames_by_video(
            video_id=video_id,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            order=order
        )
        
        # Get total count for pagination
        total = await video_frame_crud_instance.count_video_frames_by_video(video_id)
        
        # Convert to response format and ensure datetime is in GMT+7
        frame_items = []
        for frame in frames:
            frame_item = FrameItem(
                frame_id=frame.frame_id,
                ts=frame.ts,
                local_path=frame.local_path,
                updated_at=get_gmt7_time(frame.updated_at or frame.created_at)
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