from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
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
from common_py.database import DatabaseManager  # Import DatabaseManager
from api.dependency import get_db, get_job_service


router = APIRouter()

# Dependency functions use the centralized dependency module


def get_product_image_crud(db: DatabaseManager = Depends(get_db)) -> ProductImageCRUD:
    return ProductImageCRUD(db)


def get_video_frame_crud(db: DatabaseManager = Depends(get_db)) -> VideoFrameCRUD:
    return VideoFrameCRUD(db)


def get_product_crud(db: DatabaseManager = Depends(get_db)) -> ProductCRUD:
    return ProductCRUD(db)


def get_video_crud(db: DatabaseManager = Depends(get_db)) -> VideoCRUD:
    return VideoCRUD(db)


def get_gmt7_time(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert datetime to GMT+7 timezone"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(pytz.timezone('Asia/Saigon'))


async def get_job_or_404(
    job_id: str, job_service: JobService = Depends(get_job_service)
):
    """Get job or raise 404 if not found"""
    job_status = await job_service.get_job_status(job_id)

    # If job_status.phase is "unknown", it means the job was not found in the database
    if job_status.phase == "unknown":
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = {
        "job_id": job_status.job_id,
        "updated_at": job_status.updated_at,
        "phase": job_status.phase,
        "percent": job_status.percent,
        "counts": job_status.counts
    }
    return job


def calculate_feature_progress(done: int, total: int) -> dict:
    """Calculate feature progress with done count and percentage"""
    if total == 0:
        return {"done": 0, "percent": 0.0}
    return {"done": done, "percent": round((done / total) * 100, 2)}


@router.get("/jobs/{job_id}/features/summary", response_model=FeaturesSummaryResponse)
async def get_features_summary(
    job_id: str,
    db: DatabaseManager = Depends(get_db),
    product_image_crud: ProductImageCRUD = Depends(get_product_image_crud),
    video_frame_crud: VideoFrameCRUD = Depends(get_video_frame_crud),
    job_service: JobService = Depends(get_job_service)
):
    """
    Get features summary for a job including counts and progress for product images and video frames.
    """
    try:
        # Validate job exists
        await get_job_or_404(job_id, job_service)

        # Get product images counts
        product_images_total = await product_image_crud.count_product_images_by_job(job_id)

        # Count product images with features
        product_images_with_segment = await product_image_crud.count_product_images_by_job(
            job_id, has_feature="segment"
        )
        product_images_with_embedding = await product_image_crud.count_product_images_by_job(
            job_id, has_feature="embedding"
        )
        product_images_with_keypoints = await product_image_crud.count_product_images_by_job(
            job_id, has_feature="keypoints"
        )

        # Get video frames counts
        video_frames_total = await video_frame_crud.count_video_frames_by_job(job_id)

        # Count video frames with features
        video_frames_with_segment = await video_frame_crud.count_video_frames_by_job(
            job_id, has_feature="segment"
        )
        video_frames_with_embedding = await video_frame_crud.count_video_frames_by_job(
            job_id, has_feature="embedding"
        )
        video_frames_with_keypoints = await video_frame_crud.count_video_frames_by_job(
            job_id, has_feature="keypoints"
        )

        # Get job updated_at
        job_record = await db.fetch_one("SELECT updated_at FROM jobs WHERE job_id = $1", job_id)
        updated_at = get_gmt7_time(
            job_record["updated_at"] if job_record else None
        )

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
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        )


@router.get("/jobs/{job_id}/features/product-images", response_model=ProductImageFeaturesResponse)
async def get_job_product_images_features(
    job_id: str,
    has: str = Query(
        "any", pattern="^(segment|embedding|keypoints|none|any)$",
        description="Filter by feature presence"
    ),
    limit: int = Query(
        10, ge=1, le=1000,
        description="Maximum number of items to return"
    ),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    sort_by: str = Query(
        "created_at", pattern="^(created_at|img_id)$", description="Field to sort by"
    ),
    order: str = Query(
        "DESC", pattern="^(ASC|DESC)$",
        description="Sort order"
    ),
    product_image_crud: ProductImageCRUD = Depends(get_product_image_crud),
    job_service: JobService = Depends(get_job_service)
):
    """
    Get product images features for a job with filtering and pagination.
    """
    try:
        # Validate job exists
        await get_job_or_404(job_id, job_service)

        # Get images with filtering and pagination
        images = await product_image_crud.list_product_images_by_job_with_features(
            job_id=job_id,
            has_feature=has,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            order=order
        )

        # Get total count for pagination
        total = await product_image_crud.count_product_images_by_job(
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
                updated_at=get_gmt7_time(image.created_at)
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
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        )


@router.get("/jobs/{job_id}/features/video-frames", response_model=VideoFrameFeaturesResponse)
async def get_job_video_frames_features(
    job_id: str,
    video_id: Optional[str] = Query(
        None, description="Filter by video ID"
    ),
    has: str = Query(
        "any", pattern="^(segment|embedding|keypoints|none|any)$",
        description="Filter by feature presence"
    ),
    limit: int = Query(
        100, ge=1, le=1000,
        description="Maximum number of items to return"
    ),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    sort_by: str = Query(
        "ts", pattern="^(ts|frame_id)$",
        description="Field to sort by"
    ),
    order: str = Query(
        "DESC", pattern="^(ASC|DESC)$",
        description="Sort order"
    ),
    video_frame_crud: VideoFrameCRUD = Depends(get_video_frame_crud),
    job_service: JobService = Depends(get_job_service)
):
    """
    Get video frames features for a job with filtering and pagination.
    """
    try:
        # Validate job exists
        await get_job_or_404(job_id, job_service)

        # Get frames with filtering and pagination
        frames = await video_frame_crud.list_video_frames_by_job_with_features(
            job_id=job_id,
            video_id=video_id,
            has_feature=has,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            order=order
        )

        # Get total count for pagination
        total = await video_frame_crud.count_video_frames_by_job(
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
                updated_at=get_gmt7_time(frame.created_at)
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
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        )


@router.get("/features/product-images/{img_id}", response_model=ProductImageFeatureItem)
async def get_product_image_feature(
    img_id: str,
    product_image_crud: ProductImageCRUD = Depends(get_product_image_crud),
    job_service: JobService = Depends(get_job_service)
):
    """
    Get a single product image feature by ID.
    """
    try:
        # Get image
        image = await product_image_crud.get_product_image(img_id)
        if not image:
            raise HTTPException(
                status_code=404, detail=f"Product image {img_id} not found"
            )

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
            updated_at=get_gmt7_time(image.created_at)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        )


@router.get("/features/video-frames/{frame_id}", response_model=VideoFrameFeatureItem)
async def get_video_frame_feature(
    frame_id: str,
    video_frame_crud: VideoFrameCRUD = Depends(get_video_frame_crud),
    job_service: JobService = Depends(get_job_service)
):
    """
    Get a single video frame feature by ID.
    """
    try:
        # Get frame
        frame = await video_frame_crud.get_video_frame(frame_id)
        if not frame:
            raise HTTPException(
                status_code=404, detail=f"Video frame {frame_id} not found"
            )

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
            updated_at=get_gmt7_time(frame.created_at)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        )
