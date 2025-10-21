"""
Test data builders used by integration tests.

These helpers generate deterministic records and contract-compliant events so
that integration tests stay aligned with the live schema without duplicating
magic strings all over the suite.
"""

from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Tuple


def build_product_image_records(job_id: str, count: int = 3) -> List[Dict[str, Any]]:
    """
    Generate product + image records for a test job.

    Each record includes the minimum fields required by the production schema.
    Uses existing test image files from /data/tests/products/ready/
    """
    # Available test files
    test_files = ["prod_001.jpg", "prod_002.jpg", "prod_003.jpg"]

    records: List[Dict[str, Any]] = []
    for idx in range(1, min(count, len(test_files)) + 1):
        product_id = f"{job_id}_product_{idx:03d}"
        records.append(
            {
                "product_id": product_id,
                "img_id": f"{job_id}_img_{idx:03d}",
                "local_path": f"/app/data/tests/products/ready/{test_files[idx-1]}",
                "src": "amazon" if idx % 2 else "ebay",
                "asin_or_itemid": f"{job_id}_ASIN_{idx:03d}",
                "marketplace": "us",
            }
        )
    return records


def build_products_image_ready_event(job_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
    """Create a schema-compliant products.image.ready event for the record."""
    return {
        "job_id": job_id,
        "product_id": record["product_id"],
        "image_id": record["img_id"],
        "local_path": record["local_path"],
    }


def build_products_images_ready_batch_event(job_id: str, total_images: int) -> Dict[str, Any]:
    """Create a products.images.ready.batch event with the given totals."""
    return {
        "job_id": job_id,
        "event_id": str(uuid.uuid4()),
        "total_images": total_images,
    }


def build_products_images_masked_batch_event(job_id: str, total_images: int) -> Dict[str, Any]:
    """Create a products.images.masked.batch event payload."""
    return {
        "job_id": job_id,
        "event_id": str(uuid.uuid4()),
        "total_images": total_images,
    }


def build_products_image_masked_event(job_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
    """Create a products.image.masked event for a single product image record."""
    return {
        "job_id": job_id,
        "event_id": str(uuid.uuid4()),
        "product_id": record["product_id"],
        "image_id": record["img_id"],
        "mask_path": record["masked_local_path"],
    }


def build_video_keyframes_masked_event(job_id: str, frame_record: Dict[str, Any]) -> Dict[str, Any]:
    """Create a video.keyframes.masked event for a single video frame record."""
    return {
        "job_id": job_id,
        "event_id": str(uuid.uuid4()),
        "video_id": frame_record["video_id"],
        "frame_id": frame_record["frame_id"],
        "mask_path": frame_record["masked_local_path"],
    }


def build_masked_product_image_records(job_id: str, count: int = 3) -> List[Dict[str, Any]]:
    """Return product image records with derived masked paths."""
    records = build_product_image_records(job_id, count)
    return add_mask_paths_to_product_records(records)


def build_video_record(job_id: str) -> Dict[str, Any]:
    """Return a single video record suitable for the videos table."""
    video_id = f"{job_id}_video_001"
    return {
        "video_id": video_id,
        "platform": "youtube",
        "url": f"https://example.com/videos/{video_id}.mp4",
    }


def build_video_frame_records(job_id: str, video_id: str, count: int = 5) -> List[Dict[str, Any]]:
    """Generate frame records for a video using existing test files."""
    # Use existing test video frame files
    test_files = ["video_001_frame_001.jpg", "video_001_frame_002.jpg", "video_001_frame_003.jpg",
                  "video_001_frame_004.jpg", "video_001_frame_005.jpg"]

    frames: List[Dict[str, Any]] = []
    for idx in range(1, min(count, len(test_files)) + 1):
        frames.append(
            {
                "frame_id": f"{video_id}_frame_{idx:03d}",
                "ts": float(idx),
                "local_path": f"/app/data/tests/videos/ready/{test_files[idx-1]}",
            }
        )
    return frames


def build_videos_keyframes_ready_event(
    job_id: str, video_id: str, frames: Iterable[Dict[str, Any]]
) -> Dict[str, Any]:
    """Create a schema-compliant videos.keyframes.ready event."""
    return {
        "job_id": job_id,
        "video_id": video_id,
        "frames": [
            {"frame_id": frame["frame_id"], "ts": frame["ts"], "local_path": frame["local_path"]}
            for frame in frames
        ],
    }


def build_videos_keyframes_ready_batch_event(
    job_id: str, total_keyframes: int
) -> Dict[str, Any]:
    """Create a videos.keyframes.ready.batch event payload."""
    return {
        "job_id": job_id,
        "event_id": str(uuid.uuid4()),
        "total_keyframes": total_keyframes,
    }


def build_video_keypoints_masked_batch_event(
    job_id: str, total_keyframes: int
) -> Dict[str, Any]:
    """Create a video.keypoints.masked.batch event payload."""
    return {
        "job_id": job_id,
        "event_id": str(uuid.uuid4()),
        "total_keyframes": total_keyframes,
    }


def add_mask_paths_to_product_records(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ensure each product record includes masked_local_path."""
    prepared: List[Dict[str, Any]] = []
    for record in records:
        item = deepcopy(record)
        if "masked_local_path" not in item:
            # For test files, use the same file as mask path (testing event flow, not actual masking)
            item["masked_local_path"] = item["local_path"]
        prepared.append(item)
    return prepared


def add_mask_paths_to_video_frames(frames: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ensure each video frame record includes masked_local_path."""
    prepared: List[Dict[str, Any]] = []
    for frame in frames:
        item = deepcopy(frame)
        if "masked_local_path" not in item:
            # For test files, use the same file as mask path (testing event flow, not actual masking)
            item["masked_local_path"] = item["local_path"]
        prepared.append(item)
    return prepared
