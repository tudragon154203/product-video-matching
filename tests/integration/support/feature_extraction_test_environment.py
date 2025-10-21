"""
Feature Extraction Phase Test Environment Setup
Provides test fixtures and utilities for feature extraction phase integration tests.
"""
from typing import Any, Dict

import pytest_asyncio

from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from support.db_cleanup import FeatureExtractionCleanup
from support.event_publisher import FeatureExtractionEventPublisher
from support.feature_extraction_spy import FeatureExtractionSpy
from support.observability_validator import ObservabilityValidator
from .test_data import (
    build_product_image_records,
    build_products_image_ready_event,
    build_products_images_masked_batch_event,
    build_products_images_ready_batch_event,
    build_video_frame_records,
    build_video_keyframes_masked_batch_event,
    build_video_record,
    build_videos_keyframes_ready_batch_event,
    build_videos_keyframes_ready_event,
)


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
        self.test_data: Dict[str, Any] = {}

    async def setup(self, test_scenario: str = "happy_path"):
        """Set up test environment for specific scenario"""
        # Clear any existing messages and ensure clean DB state
        self.spy.clear_messages()
        await self.cleanup.cleanup_test_data()

        # Load test data based on scenario
        if test_scenario == "happy_path":
            await self._setup_happy_path_data("test_feature_extraction_001")
        elif test_scenario == "partial_batch":
            await self._setup_partial_batch_data()
        elif test_scenario == "idempotency":
            await self._setup_idempotency_data()

        # Start observability capture
        self.observability.start_observability_capture()

        return self.test_data

    async def _setup_happy_path_data(self, job_id: str):
        """Set up data for happy path test"""
        product_records = build_product_image_records(job_id)
        video_record = build_video_record(job_id)
        frame_records = build_video_frame_records(job_id, video_record["video_id"])

        product_ready_events = [build_products_image_ready_event(job_id, rec) for rec in product_records]
        products_ready_batch = build_products_images_ready_batch_event(job_id, len(product_records))
        products_masked_batch = build_products_images_masked_batch_event(job_id, len(product_records))

        videos_ready_event = build_videos_keyframes_ready_event(job_id, video_record["video_id"], frame_records)
        videos_ready_batch = build_videos_keyframes_ready_batch_event(job_id, len(frame_records))
        videos_masked_batch = build_video_keyframes_masked_batch_event(job_id, len(frame_records))

        # Persist job
        await self.db_manager.execute(
            """
            INSERT INTO jobs (job_id, industry, phase, created_at, updated_at)
            VALUES ($1, 'ergonomic pillows', 'feature_extraction', NOW(), NOW())
            ON CONFLICT (job_id) DO NOTHING;
            """,
            job_id,
        )

        # Persist products and images
        for record in product_records:
            await self.db_manager.execute(
                """
                INSERT INTO products (product_id, job_id, src, asin_or_itemid, marketplace, created_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (product_id) DO NOTHING;
                """,
                record["product_id"],
                job_id,
                record["src"],
                record["asin_or_itemid"],
                record["marketplace"],
            )

            await self.db_manager.execute(
                """
                INSERT INTO product_images (img_id, product_id, local_path, created_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (img_id) DO NOTHING;
                """,
                record["img_id"],
                record["product_id"],
                record["local_path"],
            )

        # Persist video and frames
        await self.db_manager.execute(
            """
            INSERT INTO videos (video_id, job_id, platform, url, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (video_id) DO NOTHING;
            """,
            video_record["video_id"],
            job_id,
            video_record["platform"],
            video_record["url"],
        )

        for frame in frame_records:
            await self.db_manager.execute(
                """
                INSERT INTO video_frames (frame_id, video_id, ts, local_path, created_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (frame_id) DO NOTHING;
                """,
                frame["frame_id"],
                video_record["video_id"],
                frame["ts"],
                frame["local_path"],
            )

        self.test_data = {
            "job_id": job_id,
            "products": product_records,
            "video": video_record,
            "frames": frame_records,
            "events": {
                "products_ready_batch": products_ready_batch,
                "product_ready": product_ready_events,
                "products_masked_batch": products_masked_batch,
                "videos_ready_event": videos_ready_event,
                "videos_ready_batch": videos_ready_batch,
                "videos_masked_batch": videos_masked_batch,
            },
        }

    async def _setup_partial_batch_data(self):
        """Set up data for partial batch processing test"""
        await self._setup_happy_path_data("test_feature_extraction_002")

    async def _setup_idempotency_data(self):
        """Set up data for idempotency test"""
        await self._setup_happy_path_data("test_feature_extraction_idempotency")

    async def publish_ready_events(self):
        """Publish the ready batch events to trigger feature extraction"""
        events = self.test_data["events"]

        for event in events["product_ready"]:
            await self.publisher.publish_products_image_ready(event)

        await self.publisher.publish_products_images_ready_batch(events["products_ready_batch"])

        await self.publisher.publish_video_keyframes_ready(events["videos_ready_event"])
        await self.publisher.publish_video_keyframes_ready_batch(events["videos_ready_batch"])

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
            """
            SELECT COUNT(*) as count
            FROM product_images pi
            JOIN products p ON pi.product_id = p.product_id
            WHERE p.job_id = $1 AND (pi.emb_rgb IS NOT NULL OR pi.emb_gray IS NOT NULL)
            """,
            job_id,
        )

        # Check keypoints were created
        keypoints_count = await self.db_manager.fetch_one(
            """
            SELECT COUNT(*) as count
            FROM product_images pi
            JOIN products p ON pi.product_id = p.product_id
            WHERE p.job_id = $1 AND pi.kp_blob_path IS NOT NULL
            """,
            job_id,
        )

        # Check video keypoints were created
        video_keypoints_count = await self.db_manager.fetch_one(
            """
            SELECT COUNT(*) as count
            FROM video_frames vf
            JOIN videos v ON vf.video_id = v.video_id
            WHERE v.job_id = $1 AND vf.kp_blob_path IS NOT NULL
            """,
            job_id,
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
