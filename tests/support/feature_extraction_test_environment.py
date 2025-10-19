"""
Feature Extraction Phase Test Environment Setup
Provides test fixtures and utilities for feature extraction phase integration tests.
"""
import asyncio
from typing import Dict, Any, List
import pytest_asyncio

from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from support.feature_extraction_spy import FeatureExtractionSpy
from support.db_cleanup import FeatureExtractionCleanup
from support.observability_validator import ObservabilityValidator
from support.event_publisher import FeatureExtractionEventPublisher
from tests.mock_data.verify_fixtures import load_mock_data


class FeatureExtractionTestEnvironment:
    """Complete test environment for feature extraction phase tests"""

    def __init__(
        self,
        db_manager: DatabaseManager,
        message_broker: MessageBroker,
        spy: FeatureExtractionSpy,
        cleanup: FeatureExtractionCleanup,
        observability: ObservabilityValidator,
        publisher: FeatureExtractionEventPublisher
    ):
        self.db_manager = db_manager
        self.message_broker = message_broker
        self.spy = spy
        self.cleanup = cleanup
        self.observability = observability
        self.publisher = publisher
        self.test_data = {}

    async def setup(self, test_scenario: str = "happy_path"):
        """Set up test environment for specific scenario"""
        # Clear any existing messages and ensure clean DB state
        self.spy.clear_messages()
        await self.cleanup.cleanup_test_data()

        # Load test data based on scenario
        if test_scenario == "happy_path":
            await self._setup_happy_path_data()
        elif test_scenario == "partial_batch":
            await self._setup_partial_batch_data()
        elif test_scenario == "idempotency":
            await self._setup_idempotency_data()

        # Start observability capture
        self.observability.start_observability_capture()

        return self.test_data

    async def _setup_happy_path_data(self):
        """Set up data for happy path test"""
        self.test_data = {
            "job_id": "test_feature_extraction_001",
            "products_ready": load_mock_data("products_images_ready_batch"),
            "videos_ready": load_mock_data("video_keyframes_ready_batch"),
            "expected_masked_products": load_mock_data("products_images_masked_batch"),
            "expected_masked_videos": load_mock_data("video_keyframes_masked_batch")
        }

        # Create job record
        await self.db_manager.execute(
            """
            INSERT INTO jobs (job_id, industry, phase, created_at, updated_at)
            VALUES ($1, 'ergonomic pillows', 'feature_extraction', NOW(), NOW())
            ON CONFLICT (job_id) DO NOTHING;
            """,
            self.test_data["job_id"]
        )

        # Insert product records
        for img in self.test_data["products_ready"]["ready_images"]:
            await self.db_manager.execute(
                """
                INSERT INTO products (product_id, job_id, src, asin_or_itemid, created_at, updated_at)
                VALUES ($1, $2, $3, $4, NOW(), NOW())
                ON CONFLICT (product_id) DO NOTHING;
                """,
                img["product_id"], self.test_data["job_id"], img["src"], img["asin_or_itemid"]
            )

            await self.db_manager.execute(
                """
                INSERT INTO product_images (product_id, image_path, created_at, updated_at)
                VALUES ($1, $2, NOW(), NOW())
                ON CONFLICT (product_id, image_path) DO NOTHING;
                """,
                img["product_id"], img["ready_path"]
            )

        # Insert video records
        for frame in self.test_data["videos_ready"]["ready_keyframes"]:
            await self.db_manager.execute(
                """
                INSERT INTO videos (video_id, job_id, platform, created_at, updated_at)
                VALUES ($1, $2, 'youtube', NOW(), NOW())
                ON CONFLICT (video_id) DO NOTHING;
                """,
                frame["video_id"], self.test_data["job_id"]
            )

            await self.db_manager.execute(
                """
                INSERT INTO video_frames (video_id, frame_sequence, frame_path, created_at, updated_at)
                VALUES ($1, $2, $3, NOW(), NOW())
                ON CONFLICT (video_id, frame_sequence) DO NOTHING;
                """,
                frame["video_id"], frame["frame_sequence"], frame["ready_path"]
            )

    async def _setup_partial_batch_data(self):
        """Set up data for partial batch processing test"""
        self.test_data = {
            "job_id": "test_feature_extraction_002",
            "products_ready": load_mock_data("products_images_ready_batch_partial"),
            "videos_ready": load_mock_data("video_keyframes_ready_batch")
        }

        # Similar setup as happy path but with partial batch data
        await self._setup_happy_path_data()  # Base setup
        self.test_data["job_id"] = "test_feature_extraction_002"

    async def _setup_idempotency_data(self):
        """Set up data for idempotency test"""
        # Use same data as happy path
        await self._setup_happy_path_data()

    async def publish_ready_events(self):
        """Publish the ready batch events to trigger feature extraction"""
        # Publish products ready event
        await self.publisher.publish_products_images_ready_batch(
            self.test_data["products_ready"]
        )

        # Publish videos ready event
        await self.publisher.publish_video_keyframes_ready_batch(
            self.test_data["videos_ready"]
        )

    async def wait_for_feature_completion(self, timeout: float = 300.0):
        """Wait for all feature extraction completion events"""
        job_id = self.test_data["job_id"]

        # Wait for masking phase
        products_masked = await self.spy.wait_for_products_images_masked(job_id, timeout)
        videos_masked = await self.spy.wait_for_video_keyframes_masked(job_id, timeout)

        # Wait for feature extraction phase
        embeddings_completed = await self.spy.wait_for_image_embeddings_completed(job_id, timeout)
        keypoints_completed = await self.spy.wait_for_image_keypoints_completed(job_id, timeout)
        video_keypoints_completed = await self.spy.wait_for_video_keypoints_completed(job_id, timeout)

        return {
            "products_masked": products_masked,
            "videos_masked": videos_masked,
            "embeddings_completed": embeddings_completed,
            "keypoints_completed": keypoints_completed,
            "video_keypoints_completed": video_keypoints_completed
        }

    async def validate_database_state(self):
        """Validate that database was updated correctly"""
        job_id = self.test_data["job_id"]

        # Check embeddings were created
        embeddings_count = await self.db_manager.fetch_one(
            "SELECT COUNT(*) as count FROM image_embeddings WHERE product_id IN "
            "(SELECT product_id FROM products WHERE job_id = $1)",
            job_id
        )

        # Check keypoints were created
        keypoints_count = await self.db_manager.fetch_one(
            "SELECT COUNT(*) as count FROM image_keypoints WHERE product_id IN "
            "(SELECT product_id FROM products WHERE job_id = $1)",
            job_id
        )

        # Check video keypoints were created
        video_keypoints_count = await self.db_manager.fetch_one(
            "SELECT COUNT(*) as count FROM video_keypoints WHERE video_id IN "
            "(SELECT video_id FROM videos WHERE job_id = $1)",
            job_id
        )

        return {
            "embeddings_count": embeddings_count["count"],
            "keypoints_count": keypoints_count["count"],
            "video_keypoints_count": video_keypoints_count["count"]
        }

    async def teardown(self):
        """Clean up test environment"""
        try:
            self.observability.stop_observability_capture()
            self.observability.clear_all_captures()
        finally:
            await self.cleanup.cleanup_test_data()


@pytest_asyncio.fixture
async def feature_extraction_test_environment(
    db_manager,
    message_broker,
    feature_extraction_spy,
    feature_extraction_cleanup,
    observability_validator,
    feature_extraction_event_publisher
):
    """Feature extraction test environment fixture"""
    env = FeatureExtractionTestEnvironment(
        db_manager,
        message_broker,
        feature_extraction_spy,
        feature_extraction_cleanup,
        observability_validator,
        feature_extraction_event_publisher
    )

    yield env

    await env.teardown()