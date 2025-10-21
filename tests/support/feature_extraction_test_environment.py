"""
Feature Extraction Phase Test Environment Setup (shared support module).
Provides fixtures and utilities for feature extraction phase tests outside the
integration suite. Mirrors the integration helpers but keeps a slimmer surface.
"""
from typing import Any, Dict, List

import pytest_asyncio

from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from support.feature_extraction_spy import FeatureExtractionSpy
from support.db_cleanup import FeatureExtractionCleanup
from support.observability_validator import ObservabilityValidator
from support.event_publisher import FeatureExtractionEventPublisher
from tests.integration.support.test_data import (
    build_product_image_records,
    build_products_images_ready_batch_event,
    build_video_frame_records,
    build_video_keyframes_ready_batch_event,
    build_video_record,
)


class FeatureExtractionTestEnvironment:
    """Complete test environment for feature extraction phase tests."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        message_broker: MessageBroker,
        spy: FeatureExtractionSpy,
        cleanup: FeatureExtractionCleanup,
        observability: ObservabilityValidator,
        publisher: FeatureExtractionEventPublisher,
    ):
        self.db_manager = db_manager
        self.message_broker = message_broker
        self.spy = spy
        self.cleanup = cleanup
        self.observability = observability
        self.publisher = publisher
        self.test_data: Dict[str, Any] = {}

    async def setup(self, test_scenario: str = "happy_path"):
        """Set up test environment for specific scenario."""
        self.spy.clear_messages()
        await self.cleanup.cleanup_test_data()

        if test_scenario == "happy_path":
            await self._setup_happy_path_data()
        elif test_scenario == "partial_batch":
            await self._setup_partial_batch_data()
        elif test_scenario == "idempotency":
            await self._setup_idempotency_data()

        self.observability.start_observability_capture()
        return self.test_data

    async def _setup_happy_path_data(self):
        job_id = "test_feature_extraction_support_001"
        product_records = build_product_image_records(job_id)
        video = build_video_record(job_id)
        frames = build_video_frame_records(job_id, video["video_id"])

        await self._persist_job(job_id)
        await self._persist_products(job_id, product_records)
        await self._persist_video(job_id, video, frames)

        self.test_data = {
            "job_id": job_id,
            "products_ready": build_products_images_ready_batch_event(job_id, len(product_records)),
            "videos_ready": build_video_keyframes_ready_batch_event(job_id, len(frames)),
            "products_records": product_records,
            "video": video,
            "frames": frames,
        }

    async def _setup_partial_batch_data(self):
        await self._setup_happy_path_data()
        self.test_data["job_id"] = "test_feature_extraction_support_partial"

    async def _setup_idempotency_data(self):
        await self._setup_happy_path_data()
        self.test_data["job_id"] = "test_feature_extraction_support_idempotency"

    async def publish_ready_events(self):
        await self.publisher.publish_products_images_ready_batch(self.test_data["products_ready"])
        await self.publisher.publish_video_keyframes_ready_batch(self.test_data["videos_ready"])

    async def wait_for_feature_completion(self, timeout: float = 300.0):
        job_id = self.test_data["job_id"]
        products_masked = await self.spy.wait_for_products_images_masked(job_id, timeout)
        videos_masked = await self.spy.wait_for_video_keyframes_masked(job_id, timeout)
        embeddings_completed = await self.spy.wait_for_image_embeddings_completed(job_id, timeout)
        keypoints_completed = await self.spy.wait_for_image_keypoints_completed(job_id, timeout)
        video_keypoints_completed = await self.spy.wait_for_video_keypoints_completed(job_id, timeout)
        return {
            "products_masked": products_masked,
            "videos_masked": videos_masked,
            "embeddings_completed": embeddings_completed,
            "keypoints_completed": keypoints_completed,
            "video_keypoints_completed": video_keypoints_completed,
        }

    async def validate_database_state(self):
        job_id = self.test_data["job_id"]
        embeddings_count = await self.db_manager.fetch_val(
            "SELECT COUNT(*) FROM product_images pi JOIN products p ON pi.product_id = p.product_id "
            "WHERE p.job_id = $1 AND (pi.emb_rgb IS NOT NULL OR pi.emb_gray IS NOT NULL)",
            job_id,
        )
        keypoints_count = await self.db_manager.fetch_val(
            "SELECT COUNT(*) FROM product_images pi JOIN products p ON pi.product_id = p.product_id "
            "WHERE p.job_id = $1 AND pi.kp_blob_path IS NOT NULL",
            job_id,
        )
        video_keypoints_count = await self.db_manager.fetch_val(
            "SELECT COUNT(*) FROM video_frames vf JOIN videos v ON vf.video_id = v.video_id "
            "WHERE v.job_id = $1 AND vf.kp_blob_path IS NOT NULL",
            job_id,
        )
        return {
            "embeddings_count": embeddings_count or 0,
            "keypoints_count": keypoints_count or 0,
            "video_keypoints_count": video_keypoints_count or 0,
        }

    async def teardown(self):
        try:
            self.observability.stop_observability_capture()
            self.observability.clear_all_captures()
        finally:
            await self.cleanup.cleanup_test_data()

    async def _persist_job(self, job_id: str):
        await self.db_manager.execute(
            """
            INSERT INTO jobs (job_id, industry, phase, created_at, updated_at)
            VALUES ($1, 'ergonomic pillows', 'feature_extraction', NOW(), NOW())
            ON CONFLICT (job_id) DO NOTHING;
            """,
            job_id,
        )

    async def _persist_products(self, job_id: str, product_records: List[Dict[str, Any]]):
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
                "us",
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

    async def _persist_video(self, job_id: str, video: Dict[str, Any], frames: List[Dict[str, Any]]):
        await self.db_manager.execute(
            """
            INSERT INTO videos (video_id, job_id, platform, url, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (video_id) DO NOTHING;
            """,
            video["video_id"],
            job_id,
            video["platform"],
            video["url"],
        )

        for frame in frames:
            await self.db_manager.execute(
                """
                INSERT INTO video_frames (frame_id, video_id, ts, local_path, created_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (frame_id) DO NOTHING;
                """,
                frame["frame_id"],
                video["video_id"],
                frame["ts"],
                frame["local_path"],
            )


@pytest_asyncio.fixture
async def feature_extraction_test_environment(
    db_manager,
    message_broker,
    feature_extraction_spy,
    feature_extraction_cleanup,
    observability_validator,
    feature_extraction_event_publisher,
):
    env = FeatureExtractionTestEnvironment(
        db_manager,
        message_broker,
        feature_extraction_spy,
        feature_extraction_cleanup,
        observability_validator,
        feature_extraction_event_publisher,
    )
    yield env
    await env.teardown()
