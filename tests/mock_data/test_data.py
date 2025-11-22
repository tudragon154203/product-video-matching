"""
Test data builders used by integration tests.

These helpers generate deterministic records and contract-compliant events so
that integration tests stay aligned with the live schema without duplicating
magic strings all over the suite.
"""

from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any, Dict, Iterable, List


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


def build_match_request_event(job_id: str, event_id: str = None) -> Dict[str, Any]:
    """Create a schema-compliant match.request event."""
    return {
        "job_id": job_id,
        "event_id": event_id or str(uuid.uuid4()),
    }


def build_product_images_with_embeddings(job_id: str, count: int = 3) -> List[Dict[str, Any]]:
    """Generate product image records with deterministic embeddings for matching tests."""
    records = build_masked_product_image_records(job_id, count)

    # Add deterministic embedding values that will pass similarity thresholds
    for idx, record in enumerate(records):
        record.update({
            "emb_rgb": [0.1 + idx * 0.1] * 512,  # 512-dimensional CLIP embeddings
            "emb_gray": [0.2 + idx * 0.05] * 512,
            "kp_blob_path": f"/app/data/tests/keypoints/product_{idx+1}_keypoints.npz",
        })

    return records


def build_video_frames_with_embeddings(job_id: str, video_id: str, count: int = 5) -> List[Dict[str, Any]]:
    """Generate video frame records with deterministic embeddings for matching tests."""
    frames = build_video_frame_records(job_id, video_id, count)
    frames = add_mask_paths_to_video_frames(frames)

    # Add deterministic embedding values that will create good matches
    for idx, frame in enumerate(frames):
        frame.update({
            "emb_rgb": [0.15 + idx * 0.08] * 512,  # Similar to product embeddings
            "emb_gray": [0.18 + idx * 0.04] * 512,
            "kp_blob_path": f"/app/data/tests/keypoints/frame_{idx+1}_keypoints.npz",
        })

    return frames


def build_expected_match_result_event(job_id: str, product_id: str, video_id: str,
                                      img_id: str, frame_id: str, score: float = 0.85) -> Dict[str, Any]:
    """Create an expected match.result event for test validation."""
    return {
        "job_id": job_id,
        "product_id": product_id,
        "video_id": video_id,
        "best_pair": {
            "img_id": img_id,
            "frame_id": frame_id,
            "score_pair": score,
        },
        "score": score,
        "ts": 1.0,  # Default timestamp
    }


def build_expected_match_request_completed_event(job_id: str, event_id: str = None) -> Dict[str, Any]:
    """Create an expected match.request.completed event for test validation."""
    return {
        "job_id": job_id,
        "event_id": event_id or str(uuid.uuid4()),
    }


def build_matching_test_dataset(job_id: str, num_products: int = 3, num_frames: int = 5) -> Dict[str, Any]:
    """Build a complete test dataset for matching phase integration tests."""

    # Create video and frames
    video_record = build_video_record(job_id)
    video_id = video_record["video_id"]
    frames = build_video_frames_with_embeddings(job_id, video_id, num_frames)

    # Create products with images
    product_records = build_product_images_with_embeddings(job_id, num_products)

    # Build match request event
    match_request = build_match_request_event(job_id)

    # Build expected results (first product matches first frame with high score)
    product_id = product_records[0]["product_id"] if product_records else f"{job_id}_product_001"
    img_id = product_records[0]["img_id"] if product_records else f"{job_id}_img_001"
    frame_id = frames[0]["frame_id"] if frames else f"{video_id}_frame_001"

    expected_match_result = build_expected_match_result_event(
        job_id, product_id, video_id, img_id, frame_id, 0.92
    )

    return {
        "job_id": job_id,
        "video_record": video_record,
        "frames": frames,
        "product_records": product_records,
        "match_request": match_request,
        "expected_match_result": expected_match_result,
    }


def build_low_similarity_matching_dataset(job_id: str) -> Dict[str, Any]:
    """Build dataset with low similarity to test zero-match scenario."""

    # Create video and frames with very different embeddings
    video_record = build_video_record(job_id)
    video_id = video_record["video_id"]
    frames = build_video_frames_with_embeddings(job_id, video_id, 3)

    # Create truly orthogonal embeddings - alternating positive and negative values
    # to ensure very low cosine similarity with standard product embeddings
    for idx, frame in enumerate(frames):
        frame["emb_rgb"] = [0.9 if i % 2 == 0 else -0.9 for i in range(512)]  # Orthogonal pattern
        frame["emb_gray"] = [0.8 if i % 3 == 0 else -0.8 for i in range(512)]  # Different orthogonal pattern

    # Create products with standard embeddings (all positive values)
    product_records = build_product_images_with_embeddings(job_id, 2)

    match_request = build_match_request_event(job_id)

    return {
        "job_id": job_id,
        "video_record": video_record,
        "frames": frames,
        "product_records": product_records,
        "match_request": match_request,
    }



def build_evidence_test_dataset(job_id: str, num_matches: int = 2) -> Dict[str, Any]:
    """Build a complete test dataset for evidence phase integration tests."""

    # Create video and frames
    video_record = build_video_record(job_id)
    video_id = video_record["video_id"]

    # Create products
    products = []
    product_images = []
    video_frames = []
    matches = []
    match_results = []

    for idx in range(1, num_matches + 1):
        product_id = f"{job_id}_product_{idx:03d}"
        img_id = f"{job_id}_img_{idx:03d}"
        frame_id = f"{video_id}_frame_{idx:03d}"

        # Product record
        products.append({
            "product_id": product_id,
            "src": "amazon" if idx % 2 else "ebay",
            "asin_or_itemid": f"TEST_ASIN_{idx:03d}",
            "marketplace": "us",
        })

        # Product image record
        product_images.append({
            "img_id": img_id,
            "product_id": product_id,
            "local_path": f"/app/data/tests/products/ready/prod_{idx:03d}.jpg",
        })

        # Video frame record
        video_frames.append({
            "frame_id": frame_id,
            "video_id": video_id,
            "ts": float(idx),
            "local_path": f"/app/data/tests/videos/ready/video_001_frame_{idx:03d}.jpg",
        })

        # Match record
        matches.append({
            "product_id": product_id,
            "video_id": video_id,
            "best_img_id": img_id,
            "best_frame_id": frame_id,
            "ts": float(idx),
            "score": 0.85 + (idx * 0.01),
        })

        # match.result event
        match_results.append({
            "job_id": job_id,
            "product_id": product_id,
            "video_id": video_id,
            "best_pair": {
                "img_id": img_id,
                "frame_id": frame_id,
                "score_pair": 0.85 + (idx * 0.01),
            },
            "score": 0.85 + (idx * 0.01),
            "ts": float(idx),
        })

    # match.request.completed event
    match_request_completed = {
        "job_id": job_id,
        "event_id": str(uuid.uuid4()),
    }

    return {
        "job_id": job_id,
        "video_record": video_record,
        "products": products,
        "product_images": product_images,
        "video_frames": video_frames,
        "matches": matches,
        "match_results": match_results,
        "match_request_completed": match_request_completed,
    }
