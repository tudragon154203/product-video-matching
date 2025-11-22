"""
Mock matching events for integration testing.
Provides pre-built events for common matching test scenarios.
"""

from typing import Dict, Any


def get_match_request_happy_path() -> Dict[str, Any]:
    """Get a match.request event for happy path testing."""
    return {
        "job_id": "test_job_001",
        "event_id": "550e8400-e29b-41d4-a716-446655440001",
    }


def get_match_request_idempotency_test() -> Dict[str, Any]:
    """Get a match.request event for idempotency testing (duplicate event_id)."""
    return {
        "job_id": "test_job_002",
        "event_id": "550e8400-e29b-41d4-a716-446655440002",  # Same event_id will be reused
    }


def get_expected_match_result_happy_path() -> Dict[str, Any]:
    """Get expected match.result event for happy path validation."""
    return {
        "job_id": "test_job_001",
        "product_id": "test_job_001_product_001",
        "video_id": "test_job_001_video_001",
        "best_pair": {
            "img_id": "test_job_001_img_001",
            "frame_id": "test_job_001_video_001_frame_001",
            "score_pair": 0.92,
        },
        "score": 0.92,
        "ts": 1.0,
    }


def get_expected_match_request_completed() -> Dict[str, Any]:
    """Get expected match.request.completed event for validation."""
    return {
        "job_id": "test_job_001",
        "event_id": "550e8400-e29b-41d4-a716-446655440003",
    }


def get_mock_embeddings_and_keypoints() -> Dict[str, Any]:
    """Get mock embedding and keypoint data for test fixtures."""
    return {
        "product_embeddings": {
            "product_001": {
                "emb_rgb": [0.1] * 512,
                "emb_gray": [0.2] * 512,
                "kp_blob_path": "/app/data/tests/keypoints/product_001_keypoints.npz",
            },
            "product_002": {
                "emb_rgb": [0.2] * 512,
                "emb_gray": [0.25] * 512,
                "kp_blob_path": "/app/data/tests/keypoints/product_002_keypoints.npz",
            },
            "product_003": {
                "emb_rgb": [0.3] * 512,
                "emb_gray": [0.3] * 512,
                "kp_blob_path": "/app/data/tests/keypoints/product_003_keypoints.npz",
            },
        },
        "video_frame_embeddings": {
            "frame_001": {
                "emb_rgb": [0.15] * 512,
                "emb_gray": [0.18] * 512,
                "kp_blob_path": "/app/data/tests/keypoints/frame_001_keypoints.npz",
            },
            "frame_002": {
                "emb_rgb": [0.23] * 512,
                "emb_gray": [0.22] * 512,
                "kp_blob_path": "/app/data/tests/keypoints/frame_002_keypoints.npz",
            },
            "frame_003": {
                "emb_rgb": [0.31] * 512,
                "emb_gray": [0.32] * 512,
                "kp_blob_path": "/app/data/tests/keypoints/frame_003_keypoints.npz",
            },
        }
    }


def get_low_similarity_embeddings() -> Dict[str, Any]:
    """Get embeddings designed to produce low similarity (zero matches)."""
    return {
        "product_embeddings": {
            "product_001": {
                "emb_rgb": [0.1] * 512,
                "emb_gray": [0.2] * 512,
                "kp_blob_path": "/app/data/tests/keypoints/product_001_keypoints.npz",
            },
        },
        "video_frame_embeddings": {
            "frame_001": {
                "emb_rgb": [0.9] * 512,  # Very different from products
                "emb_gray": [0.8] * 512,
                "kp_blob_path": "/app/data/tests/keypoints/frame_001_keypoints.npz",
            },
        }
    }


def get_partial_asset_embeddings() -> Dict[str, Any]:
    """Get embeddings with missing keypoints to test fallback behavior."""
    return {
        "product_embeddings": {
            "product_001": {
                "emb_rgb": [0.1] * 512,
                "emb_gray": [0.2] * 512,
                "kp_blob_path": "/app/data/tests/keypoints/product_001_keypoints.npz",
            },
            "product_002": {
                "emb_rgb": [0.2] * 512,
                "emb_gray": [0.25] * 512,
                # Missing kp_blob_path to test fallback
            },
        },
        "video_frame_embeddings": {
            "frame_001": {
                "emb_rgb": [0.15] * 512,
                "emb_gray": [0.18] * 512,
                "kp_blob_path": "/app/data/tests/keypoints/frame_001_keypoints.npz",
            },
        }
    }


# Test scenarios configuration
MATCHING_TEST_SCENARIOS = {
    "happy_path": {
        "description": "Successful matching with acceptable pairs",
        "match_request": get_match_request_happy_path(),
        "expected_match_result": get_expected_match_result_happy_path(),
        "expected_completion": get_expected_match_request_completed(),
        "embeddings": get_mock_embeddings_and_keypoints(),
    },
    "zero_matches": {
        "description": "No acceptable matches due to low similarity",
        "match_request": get_match_request_happy_path(),
        "expected_match_result": None,  # No match.result expected
        "embeddings": get_low_similarity_embeddings(),
    },
    "idempotency": {
        "description": "Test duplicate event handling",
        "match_request": get_match_request_idempotency_test(),
        "embeddings": get_mock_embeddings_and_keypoints(),
    },
    "partial_assets": {
        "description": "Test fallback behavior with missing keypoints",
        "match_request": get_match_request_happy_path(),
        "embeddings": get_partial_asset_embeddings(),
    },
}
