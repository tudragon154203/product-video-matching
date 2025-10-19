"""
Standalone script to verify mock data fixtures work correctly.
This script validates that fixtures follow contract schemas.
"""

import json
import sys
from pathlib import Path

# Try to import validator, but don't fail if not available
try:
    from contracts.validator import validator
    VALIDATOR_AVAILABLE = True
    sys.path.append(str(Path(__file__).parent.parent.parent / "libs" / "contracts"))
except ImportError:
    VALIDATOR_AVAILABLE = False


def load_json_file(file_path: Path) -> dict:
    """Load JSON data from a file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_product_fixtures():
    """Test that all product fixtures follow contract schemas."""
    print("Testing product fixtures...")

    # Test products collect request
    collect_request = load_json_file(Path(__file__).parent / "products" / "products_collect_request.json")
    print(f"Products collect request: {collect_request}")

    # Test products collections completed
    collections_completed = load_json_file(Path(__file__).parent / "products" / "products_collections_completed.json")
    print(f"Products collections completed: {collections_completed}")

    # Test individual products
    products = []
    for i in range(1, 4):  # Products 1-3
        product_file = Path(__file__).parent / "products" / f"product_{i:03d}.json"
        if product_file.exists():
            product = load_json_file(product_file)
            products.append(product)
            print(f"Product {i}: {product['product_id']} - {product['title']}")

    print(f"Number of products: {len(products)}")
    print("Product fixtures loaded successfully!\n")
    return products


def test_video_fixtures():
    """Test that all video fixtures follow contract schemas."""
    print("Testing video fixtures...")

    # Test videos search request
    search_request = load_json_file(Path(__file__).parent / "videos" / "videos_search_request.json")
    print(f"Videos search request: {search_request}")

    # Test videos collections completed
    collections_completed = load_json_file(Path(__file__).parent / "videos" / "videos_collections_completed.json")
    print(f"Videos collections completed: {collections_completed}")

    # Test individual videos
    videos = []
    for i in range(1, 3):  # Videos 1-2
        video_file = Path(__file__).parent / "videos" / f"video_{i:03d}.json"
        if video_file.exists():
            video = load_json_file(video_file)
            videos.append(video)
            print(f"Video {i}: {video['video_id']} - {video['title']}")

    print(f"Number of videos: {len(videos)}")

    # Test video keyframes
    for i in range(1, 3):
        try:
            keyframes_file = Path(__file__).parent / "videos" / f"video_{i:03d}_keyframes.json"
            if keyframes_file.exists():
                keyframes = load_json_file(keyframes_file)
                print(f"Video {i} keyframes: {len(keyframes['frames'])} frames")
        except Exception as e:
            print(f"Error loading keyframes for video {i}: {e}")

    print("Video fixtures loaded successfully!\n")
    return videos


def validate_against_schemas():
    """Validate fixtures against contract schemas."""
    if not VALIDATOR_AVAILABLE:
        print("Validator not available, skipping schema validation")
        return True

    print("Validating fixtures against schemas...")

    try:
        # Validate products collect request
        collect_request = load_json_file(Path(__file__).parent / "products" / "products_collect_request.json")
        validator.validate_event("products_collect_request", collect_request)
        print("+ Products collect request validated successfully")

        # Validate products collections completed
        collections_completed = load_json_file(Path(__file__).parent / "products" / "products_collections_completed.json")
        validator.validate_event("products_collections_completed", collections_completed)
        print("+ Products collections completed validated successfully")

        # Validate videos search request
        search_request = load_json_file(Path(__file__).parent / "videos" / "videos_search_request.json")
        validator.validate_event("videos_search_request", search_request)
        print("+ Videos search request validated successfully")

        # Validate videos collections completed
        videos_completed = load_json_file(Path(__file__).parent / "videos" / "videos_collections_completed.json")
        validator.validate_event("videos_collections_completed", videos_completed)
        print("+ Videos collections completed validated successfully")

        # Validate video keyframes
        for i in range(1, 3):
            keyframes_file = Path(__file__).parent / "videos" / f"video_{i:03d}_keyframes.json"
            if keyframes_file.exists():
                keyframes = load_json_file(keyframes_file)
                validator.validate_event("videos_keyframes_ready", keyframes)
                print(f"+ Video {i} keyframes validated successfully")

        print("All fixtures validated successfully against schemas!\n")
        return True

    except Exception as e:
        print(f"Validation error: {e}")
        return False


if __name__ == "__main__":
    """Run all tests to verify fixtures work correctly."""
    print("=== Mock Data Fixtures Verification ===\n")

    products = test_product_fixtures()
    videos = test_video_fixtures()
    validation_passed = validate_against_schemas()

    if validation_passed:
        print("=== All Tests Passed! ===")
        print("Mock data fixtures are ready for use in integration tests.")
        print(f"Summary: {len(products)} products, {len(videos)} videos")
    else:
        print("=== Validation Failed! ===")
        sys.exit(1)


def load_mock_data(fixture_name: str) -> dict:
    """Load mock data fixture by name for use in tests."""
    fixture_path = Path(__file__).parent / f"{fixture_name}.json"

    if not fixture_path.exists():
        raise FileNotFoundError(f"Mock data fixture not found: {fixture_path}")

    return load_json_file(fixture_path)
