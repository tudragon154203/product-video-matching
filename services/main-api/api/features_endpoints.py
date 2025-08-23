from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime, timezone
import pytz

from models.features_schemas import (
    FeaturesSummaryResponse,
    ProductImageFeaturesResponse,
    VideoFrameFeaturesResponse,
    ProductImageFeatureItem,
    VideoFrameFeatureItem
)
from services.job.job_service import JobService
from common_py.crud.product_image_crud import ProductImageCRUD
from common_py.crud.video_frame_crud import VideoFrameCRUD
from common_py.crud.product_crud import ProductCRUD
from common_py.crud.video_crud import VideoCRUD


router = APIRouter()

# Global instances (will be set in main.py)
db_instance = None
job_service_instance = None
product_image_crud_instance = None
video_frame_crud_instance = None
product_crud_instance = None
video_crud_instance = None


def get_gmt7_time(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert datetime to GMT+7 timezone"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(pytz.timezone('Asia/Saigon'))


async def get_job_or_404(job_id: str):
    """Get job or raise 404 if not found"""
    job = await job_service_instance.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


def calculate_feature_progress(done: int, total: int) -> dict:
    """Calculate feature progress with done count and percentage"""
    if total == 0:
        return {"done": 0, "percent": 0.0}
    return {"done": done, "percent": round((done / total) * 100, 2)}


@router.get("/jobs/{job_id}/features/summary", response_model=FeaturesSummaryResponse)
async def get_features_summary(job_id: str):
    """
    Get features summary for a job including counts and progress for product images and video frames.
    """
    try:
        # Validate job exists
        await get_job_or_404(job_id)
        
        # Get product images counts
        product_images_total = await product_image_crud_instance.count_product_images_by_job(job_id)
        
        # Count product images with features
        product_images_with_segment = await product_image_crud_instance.count_product_images_by_job(
            job_id, has_feature="segment"
        )
        product_images_with_embedding = await product_image_crud_instance.count_product_images_by_job(
            job_id, has_feature="embedding"
        )
        product_images_with_keypoints = await product_image_crud_instance.count_product_images_by_job(
            job_id, has_feature="keypoints"
        )
        
        # Get video frames counts
        video_frames_total = await video_frame_crud_instance.count_video_frames_by_job(job_id)
        
        # Count video frames with features
        video_frames_with_segment = await video_frame_crud_instance.count_video_frames_by_job(
            job_id, has_feature="segment"
        )
        video_frames_with_embedding = await video_frame_crud_instance.count_video_frames_by_job(
            job_id, has_feature="embedding"
        )
        video_frames_with_keypoints = await video_frame_crud_instance.count_video_frames_by_job(
            job_id, has_feature="keypoints"
        )
        
        # Get job updated_at
        job_record = await db_instance.fetch_one("SELECT updated_at FROM jobs WHERE job_id = $1", job_id)
        updated_at = get_gmt7_time(job_record["updated_at"] if job_record else None)
        
        return FeaturesSummaryResponse(
            job_id=job_id,
            product_images={
                "total": product_images_total,
                "segment": calculate_feature_progress(product_images_with_segment, product_images_total),
                "embedding": calculate_feature_progress(product_images_with_embedding, product_images_total),
                "keypoints": calculate_feature_progress(product_images_with_keypoints, product_images_total)
            },
            video_frames={
                "total": video_frames_total,
                "segment": calculate_feature_progress(video_frames_with_segment, video_frames_total),
                "embedding": calculate_feature_progress(video_frames_with_embedding, video_frames_total),
                "keypoints": calculate_feature_progress(video_frames_with_keypoints, video_frames_total)
            },
            updated_at=updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/jobs/{job_id}/features/product-images", response_model=ProductImageFeaturesResponse)
async def get_job_product_images_features(
    job_id: str,
    has: str = Query("any", pattern="^(segment|embedding|keypoints|none|any)$", description="Filter by feature presence"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    sort_by: str = Query("updated_at", pattern="^(updated_at|img_id)$", description="Field to sort by"),
    order: str = Query("DESC", pattern="^(ASC|DESC)$", description="Sort order")
):
    """
    Get product images features for a job with filtering and pagination.
    """
    try:
        # Validate job exists
        await get_job_or_404(job_id)
        
        # Get images with filtering and pagination
        images = await product_image_crud_instance.list_product_images_by_job_with_features(
            job_id=job_id,
            has_feature=has,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            order=order
        )
        
        # Get total count for pagination
        total = await product_image_crud_instance.count_product_images_by_job(
            job_id=job_id,
            has_feature=has
        )
        
        # Convert to response format
        image_items = []
        for image in images:
            # Determine feature presence
            has_segment = image.masked_local_path is not None
            has_embedding = image.emb_rgb is not None or image.emb_gray is not None
            has_keypoints = image.kp_blob_path is not None
            
            # Create paths object
            paths = {
                "segment": image.masked_local_path,
                "embedding": None,  # We don't expose embedding paths directly
                "keypoints": image.kp_blob_path
            }
            
            image_item = ProductImageFeatureItem(
                img_id=image.img_id,
                product_id=image.product_id,
                has_segment=has_segment,
                has_embedding=has_embedding,
                has_keypoints=has_keypoints,
                paths=paths,
                updated_at=get_gmt7_time(image.updated_at or image.created_at)
            )
            image_items.append(image_item)
        
        return ProductImageFeaturesResponse(
            items=image_items,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/jobs/{job_id}/features/video-frames", response_model=VideoFrameFeaturesResponse)
async def get_job_video_frames_features(
    job_id: str,
    video_id: Optional[str] = Query(None, description="Filter by video ID"),
    has: str = Query("any", pattern="^(segment|embedding|keypoints|none|any)$", description="Filter by feature presence"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    sort_by: str = Query("updated_at", pattern="^(updated_at|frame_id|ts)$", description="Field to sort by"),
    order: str = Query("DESC", pattern="^(ASC|DESC)$", description="Sort order")
):
    """
    Get video frames features for a job with filtering and pagination.
    """
    try:
        # Validate job exists
        await get_job_or_404(job_id)
        
        # Get frames with filtering and pagination
        frames = await video_frame_crud_instance.list_video_frames_by_job_with_features(
            job_id=job_id,
            video_id=video_id,
            has_feature=has,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            order=order
        )
        
        # Get total count for pagination
        total = await video_frame_crud_instance.count_video_frames_by_job(
            job_id=job_id,
            video_id=video_id,
            has_feature=has
        )
        
        # Convert to response format
        frame_items = []
        for frame in frames:
            # Determine feature presence
            has_segment = frame.masked_local_path is not None
            has_embedding = frame.emb_rgb is not None or frame.emb_gray is not None
            has_keypoints = frame.kp_blob_path is not None
            
            # Create paths object
            paths = {
                "segment": frame.masked_local_path,
                "embedding": None,  # We don't expose embedding paths directly
                "keypoints": frame.kp_blob_path
            }
            
            frame_item = VideoFrameFeatureItem(
                frame_id=frame.frame_id,
                video_id=frame.video_id,
                ts=frame.ts,
                has_segment=has_segment,
                has_embedding=has_embedding,
                has_keypoints=has_keypoints,
                paths=paths,
                updated_at=get_gmt7_time(frame.updated_at or frame.created_at)
            )
            frame_items.append(frame_item)
        
        return VideoFrameFeaturesResponse(
            items=frame_items,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/features/product-images/{img_id}", response_model=ProductImageFeatureItem)
async def get_product_image_feature(img_id: str):
    """
    Get a single product image feature by ID.
    """
    try:
        # Get image
        image = await product_image_crud_instance.get_product_image(img_id)
        if not image:
            raise HTTPException(status_code=404, detail=f"Product image {img_id} not found")
        
        # Determine feature presence
        has_segment = image.masked_local_path is not None
        has_embedding = image.emb_rgb is not None or image.emb_gray is not None
        has_keypoints = image.kp_blob_path is not None
        
        # Create paths object
        paths = {
            "segment": image.masked_local_path,
            "embedding": None,  # We don't expose embedding paths directly
            "keypoints": image.kp_blob_path
        }
        
        return ProductImageFeatureItem(
            img_id=image.img_id,
            product_id=image.product_id,
            has_segment=has_segment,
            has_embedding=has_embedding,
            has_keypoints=has_keypoints,
            paths=paths,
            updated_at=get_gmt7_time(image.updated_at or image.created_at)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/features/video-frames/{frame_id}", response_model=VideoFrameFeatureItem)
async def get_video_frame_feature(frame_id: str):
    """
    Get a single video frame feature by ID.
    """
    try:
        # Get frame
        frame = await video_frame_crud_instance.get_video_frame(frame_id)
        if not frame:
            raise HTTPException(status_code=404, detail=f"Video frame {frame_id} not found")
        
        # Determine feature presence
        has_segment = frame.masked_local_path is not None
        has_embedding = frame.emb_rgb is not None or frame.emb_gray is not None
        has_keypoints = frame.kp_blob_path is not None
        
        # Create paths object
        paths = {
            "segment": frame.masked_local_path,
            "embedding": None,  # We don't expose embedding paths directly
            "keypoints": frame.kp_blob_path
        }
        
        return VideoFrameFeatureItem(
            frame_id=frame.frame_id,
            video_id=frame.video_id,
            ts=frame.ts,
            has_segment=has_segment,
            has_embedding=has_embedding,
            has_keypoints=has_keypoints,
            paths=paths,
            updated_at=get_gmt7_time(frame.updated_at or frame.created_at)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")