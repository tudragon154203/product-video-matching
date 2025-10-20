"""
Mock data fixtures for testing.
Provides consistent payloads for integration tests without external dependencies.
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Any

# Get the mock data directory path
MOCK_DATA_DIR = Path(__file__).parent.parent


class MockDataLoader:
    """Utility class for loading mock data fixtures."""

    @staticmethod
    def load_json_file(file_path: Path) -> Dict[str, Any]:
        """Load JSON data from a file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def get_products_collect_request() -> Dict[str, Any]:
        """Get products collect request fixture."""
        return MockDataLoader.load_json_file(
            MOCK_DATA_DIR / "events" / "collection" / "products_collect_request.json"
        )

    @staticmethod
    def get_products_collections_completed() -> Dict[str, Any]:
        """Get products collections completed fixture."""
        return MockDataLoader.load_json_file(
            MOCK_DATA_DIR / "events" / "collection" / "products_collections_completed.json"
        )

    @staticmethod
    def get_all_products() -> List[Dict[str, Any]]:
        """Get all product fixtures."""
        products = []
        for i in range(1, 4):  # Products 1-3
            product_file = MOCK_DATA_DIR / "entities" / "products" / f"product_{i:03d}.json"
            if product_file.exists():
                products.append(MockDataLoader.load_json_file(product_file))
        return products

    @staticmethod
    def get_product(product_id: int) -> Dict[str, Any]:
        """Get a specific product fixture by ID (1-3)."""
        product_file = MOCK_DATA_DIR / "entities" / "products" / f"product_{product_id:03d}.json"
        return MockDataLoader.load_json_file(product_file)

    @staticmethod
    def get_videos_search_request() -> Dict[str, Any]:
        """Get videos search request fixture."""
        return MockDataLoader.load_json_file(
            MOCK_DATA_DIR / "events" / "collection" / "videos_search_request.json"
        )

    @staticmethod
    def get_videos_collections_completed() -> Dict[str, Any]:
        """Get videos collections completed fixture."""
        return MockDataLoader.load_json_file(
            MOCK_DATA_DIR / "events" / "collection" / "videos_collections_completed.json"
        )

    @staticmethod
    def get_all_videos() -> List[Dict[str, Any]]:
        """Get all video fixtures."""
        videos = []
        for i in range(1, 3):  # Videos 1-2
            video_file = MOCK_DATA_DIR / "entities" / "videos" / f"video_{i:03d}.json"
            if video_file.exists():
                videos.append(MockDataLoader.load_json_file(video_file))
        return videos

    @staticmethod
    def get_video(video_id: int) -> Dict[str, Any]:
        """Get a specific video fixture by ID (1-2)."""
        video_file = MOCK_DATA_DIR / "entities" / "videos" / f"video_{video_id:03d}.json"
        return MockDataLoader.load_json_file(video_file)

    @staticmethod
    def get_video_keyframes(video_id: int) -> Dict[str, Any]:
        """Get keyframes for a specific video by ID (1-2)."""
        keyframes_file = MOCK_DATA_DIR / "entities" / "videos" / f"video_{video_id:03d}_keyframes.json"
        return MockDataLoader.load_json_file(keyframes_file)

    @staticmethod
    def generate_test_event_id() -> str:
        """Generate a deterministic test event ID."""
        return str(uuid.UUID('550e8400-e29b-41d4-a716-446655440000'))

    @staticmethod
    def generate_test_job_id(prefix: str = "test_job") -> str:
        """Generate a deterministic test job ID."""
        return f"{prefix}_mock_001"


# Convenience functions for direct import
def get_products_collect_request() -> Dict[str, Any]:
    """Get products collect request fixture."""
    return MockDataLoader.get_products_collect_request()


def get_products_collections_completed() -> Dict[str, Any]:
    """Get products collections completed fixture."""
    return MockDataLoader.get_products_collections_completed()


def get_all_products() -> List[Dict[str, Any]]:
    """Get all product fixtures."""
    return MockDataLoader.get_all_products()


def get_videos_search_request() -> Dict[str, Any]:
    """Get videos search request fixture."""
    return MockDataLoader.get_videos_search_request()


def get_videos_collections_completed() -> Dict[str, Any]:
    """Get videos collections completed fixture."""
    return MockDataLoader.get_videos_collections_completed()


def get_all_videos() -> List[Dict[str, Any]]:
    """Get all video fixtures."""
    return MockDataLoader.get_all_videos()
