"""
Example usage of mock data fixtures for integration tests.
This demonstrates how to use the fixtures in your test code.
"""

from fixtures import MockDataLoader
import sys
from pathlib import Path

# Add paths for imports
sys.path.append(str(Path(__file__).parent.parent / "libs" / "contracts"))
sys.path.append(str(Path(__file__).parent))


def example_product_collection_test():
    """Example: Testing product collection workflow."""
    print("=== Example: Product Collection Test ===")

    # Load the products collect request
    collect_request = MockDataLoader.get_products_collect_request()
    print(f"Starting product collection job: {collect_request['job_id']}")

    # Simulate processing...
    print("Processing product collection...")

    # Get the products that would be collected
    products = MockDataLoader.get_all_products()
    print(f"Collected {len(products)} products:")
    for product in products:
        print(f"  - {product['product_id']}: {product['title']}")

    # Load the completion event
    completion = MockDataLoader.get_products_collections_completed()
    print(f"Product collection completed: {completion['event_id']}")
    print()


def example_video_search_test():
    """Example: Testing video search workflow."""
    print("=== Example: Video Search Test ===")

    # Load the videos search request
    search_request = MockDataLoader.get_videos_search_request()
    print(f"Starting video search job: {search_request['job_id']}")
    print(f"Industry: {search_request['industry']}")
    print(f"Platforms: {search_request['platforms']}")

    # Simulate processing...
    print("Processing video search...")

    # Get the videos that would be found
    videos = MockDataLoader.get_all_videos()
    print(f"Found {len(videos)} videos:")
    for video in videos:
        print(f"  - {video['video_id']}: {video['title']} ({video['platform']})")

    # Load the completion event
    completion = MockDataLoader.get_videos_collections_completed()
    print(f"Video search completed: {completion['event_id']}")
    print()


def example_keyframe_processing_test():
    """Example: Testing keyframe processing workflow."""
    print("=== Example: Keyframe Processing Test ===")

    # Get videos and their keyframes
    videos = MockDataLoader.get_all_videos()

    for i, video in enumerate(videos, 1):
        keyframes = MockDataLoader.get_video_keyframes(i)

        print(f"Processing keyframes for {video['title']}:")
        print(f"  Video ID: {video['video_id']}")
        print(f"  Duration: {video['duration_s']}s")
        print(f"  Keyframes: {len(keyframes['frames'])}")

        for frame in keyframes['frames']:
            print(f"    - Frame {frame['frame_id']} at {frame['ts']}s")
        print()


def example_deterministic_test_data():
    """Example: Using deterministic test data for consistent results."""
    print("=== Example: Deterministic Test Data ===")

    # Generate deterministic IDs
    job_id = MockDataLoader.generate_test_job_id("integration_test")
    event_id = MockDataLoader.generate_test_event_id()

    print(f"Deterministic Job ID: {job_id}")
    print(f"Deterministic Event ID: {event_id}")

    # Load specific products by ID
    product_1 = MockDataLoader.get_product(1)
    product_2 = MockDataLoader.get_product(2)

    print(f"Product 1 ID: {product_1['product_id']}")
    print(f"Product 2 ID: {product_2['product_id']}")

    # Load specific videos by ID
    video_1 = MockDataLoader.get_video(1)
    video_2 = MockDataLoader.get_video(2)

    print(f"Video 1 ID: {video_1['video_id']}")
    print(f"Video 2 ID: {video_2['video_id']}")
    print()


if __name__ == "__main__":
    """Run all examples to demonstrate fixture usage."""
    print("=== Mock Data Fixtures Usage Examples ===\n")

    example_product_collection_test()
    example_video_search_test()
    example_keyframe_processing_test()
    example_deterministic_test_data()

    print("=== Examples Complete ===")
    print("You can now use these patterns in your integration tests!")
