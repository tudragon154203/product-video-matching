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
    """
    records: List[Dict[str, Any]] = []
    for idx in range(1, count + 1):
        product_id = f"{job_id}_product_{idx:03d}"
        records.append(
            {
                "product_id": product_id,
                "img_id": f"{job_id}_img_{idx:03d}",
                "local_path": f"/data/tests/products/{job_id}/image_{idx:03d}.jpg",
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
    """Generate frame records for a video."""
    frames: List[Dict[str, Any]] = []
    for idx in range(1, count + 1):
        frames.append(
            {
                "frame_id": f"{video_id}_frame_{idx:03d}",
                "ts": float(idx),
                "local_path": f"/data/tests/videos/{job_id}/{video_id}_frame_{idx:03d}.jpg",
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


def build_video_keyframes_masked_batch_event(
    job_id: str, total_keyframes: int
) -> Dict[str, Any]:
    """Create a video.keyframes.masked.batch event payload."""
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
            item["masked_local_path"] = item["local_path"].replace("/products/", "/products/masked/")
        prepared.append(item)
    return prepared


def add_mask_paths_to_video_frames(frames: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ensure each video frame record includes masked_local_path."""
    prepared: List[Dict[str, Any]] = []
    for frame in frames:
        item = deepcopy(frame)
        if "masked_local_path" not in item:
            item["masked_local_path"] = item["local_path"].replace("/videos/", "/videos/masked/")
        prepared.append(item)
    return prepared
