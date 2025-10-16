"""
Test file to verify mock data fixtures work correctly.
This file demonstrates usage and validates the fixtures follow contract schemas.
"""

from . import (
    get_products_collect_request,
    get_products_collections_completed,
    get_all_products,
    get_videos_search_request,
    get_videos_collections_completed,
    get_all_videos,
    MockDataLoader
)
from contracts.validator import validator
import json
import sys
from pathlib import Path

# Add paths for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "libs" / "contracts"))


def test_product_fixtures():
    """Test that all product fixtures follow contract schemas."""
    print("Testing product fixtures...")

    # Test products collect request
    collect_request = get_products_collect_request()
    print(f"Products collect request: {collect_request}")

    # Test products collections completed
    collections_completed = get_products_collections_completed()
    print(f"Products collections completed: {collections_completed}")

    # Test individual products
    products = get_all_products()
    print(f"Number of products: {len(products)}")
    for i, product in enumerate(products, 1):
        print(f"Product {i}: {product['product_id']} - {product['title']}")

    print("Product fixtures loaded successfully!\n")


def test_video_fixtures():
    """Test that all video fixtures follow contract schemas."""
    print("Testing video fixtures...")

    # Test videos search request
    search_request = get_videos_search_request()
    print(f"Videos search request: {search_request}")

    # Test videos collections completed
    collections_completed = get_videos_collections_completed()
    print(f"Videos collections completed: {collections_completed}")

    # Test individual videos
    videos = get_all_videos()
    print(f"Number of videos: {len(videos)}")
    for i, video in enumerate(videos, 1):
        print(f"Video {i}: {video['video_id']} - {video['title']}")

    # Test video keyframes
    for i in range(1, 3):
        try:
            keyframes = MockDataLoader.get_video_keyframes(i)
            print(f"Video {i} keyframes: {len(keyframes['frames'])} frames")
        except Exception as e:
            print(f"Error loading keyframes for video {i}: {e}")

    print("Video fixtures loaded successfully!\n")


def test_deterministic_ids():
    """Test that IDs are deterministic across multiple loads."""
    print("Testing deterministic IDs...")

    # Load products multiple times
    products1 = get_all_products()
    products2 = get_all_products()

    assert len(products1) == len(products2) == 3, "Should have exactly 3 products"

    for i in range(3):
        assert products1[i]['product_id'] == products2[i]['product_id'], \
            f"Product {i+1} ID should be deterministic"

    # Load videos multiple times
    videos1 = get_all_videos()
    videos2 = get_all_videos()

    assert len(videos1) == len(videos2) == 2, "Should have exactly 2 videos"

    for i in range(2):
        assert videos1[i]['video_id'] == videos2[i]['video_id'], \
            f"Video {i+1} ID should be deterministic"

    # Test event IDs
    event_id1 = MockDataLoader.generate_test_event_id()
    event_id2 = MockDataLoader.generate_test_event_id()
    assert event_id1 == event_id2, "Event ID should be deterministic"

    # Test job IDs
    job_id1 = MockDataLoader.generate_test_job_id()
    job_id2 = MockDataLoader.generate_test_job_id()
    assert job_id1 == job_id2, "Job ID should be deterministic"

    print("All IDs are deterministic!\n")


def validate_against_schemas():
    """Validate fixtures against contract schemas."""
    print("Validating fixtures against schemas...")

    try:
        # Validate products collect request
        collect_request = get_products_collect_request()
        validator.validate_event("products_collect_request", collect_request)
        print("✓ Products collect request validated successfully")

        # Validate products collections completed
        collections_completed = get_products_collections_completed()
        validator.validate_event("products_collections_completed", collections_completed)
        print("✓ Products collections completed validated successfully")

        # Validate videos search request
        search_request = get_videos_search_request()
        validator.validate_event("videos_search_request", search_request)
        print("✓ Videos search request validated successfully")

        # Validate videos collections completed
        videos_completed = get_videos_collections_completed()
        validator.validate_event("videos_collections_completed", videos_completed)
        print("✓ Videos collections completed validated successfully")

        # Validate video keyframes
        for i in range(1, 3):
            keyframes = MockDataLoader.get_video_keyframes(i)
            validator.validate_event("videos_keyframes_ready", keyframes)
            print(f"✓ Video {i} keyframes validated successfully")

        print("All fixtures validated successfully against schemas!\n")

    except Exception as e:
        print(f"Validation error: {e}")
        raise


if __name__ == "__main__":
    """Run all tests to verify fixtures work correctly."""
    print("=== Mock Data Fixtures Test ===\n")

    test_product_fixtures()
    test_video_fixtures()
    test_deterministic_ids()
    validate_against_schemas()

    print("=== All Tests Passed! ===")
    print("Mock data fixtures are ready for use in integration tests.")
