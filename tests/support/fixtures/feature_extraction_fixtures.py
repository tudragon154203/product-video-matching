"""
Feature Extraction Fixtures
Pytest fixtures for feature extraction phase integration tests.
"""
from config import config
from support.publisher.event_publisher import FeatureExtractionEventPublisher
from support.validators.observability_validator import ObservabilityValidator
from support.validators.db_cleanup import FeatureExtractionCleanup, FeatureExtractionStateValidator
from support.spy.feature_extraction_spy import FeatureExtractionSpy
from typing import Dict, Any, List, Tuple
import pytest_asyncio
import pytest
import os
import sys
from pathlib import Path

# Early sys.path setup to resolve project modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LIBS_DIR = PROJECT_ROOT / "libs"
COMMON_PY_DIR = LIBS_DIR / "common-py"
INFRA_DIR = PROJECT_ROOT / "infra"
TESTS_DIR = PROJECT_ROOT / "tests"


def _setup_sys_path():
    """Ensure project-specific paths are available before project imports."""
    MOCK_DATA_DIR = PROJECT_ROOT / "tests" / "mock_data"
    for p in (COMMON_PY_DIR, LIBS_DIR, INFRA_DIR, PROJECT_ROOT, TESTS_DIR, MOCK_DATA_DIR):
        ps = str(p)
        if ps in sys.path:
            continue
        sys.path.insert(0, ps)


_setup_sys_path()


# Fix import path - test_data is in mock_data
try:
    from mock_data.test_data import (
        add_mask_paths_to_product_records,
        add_mask_paths_to_video_frames,
        build_product_image_records,
        build_products_image_ready_event,
        build_products_images_masked_batch_event,
        build_products_images_ready_batch_event,
        build_products_image_masked_event,
        build_video_frame_records,
        build_video_keypoints_masked_batch_event,
        build_video_keyframes_masked_event,
        build_video_record,
        build_videos_keyframes_ready_batch_event,
        build_videos_keyframes_ready_event,
    )
    print("Successfully imported from mock_data.test_data")
except ImportError as e:
    # Fallback for when running from different contexts
    print(f"Failed to import from mock_data.test_data: {e}")
    # Define minimal fallback functions to prevent NameError

    def add_mask_paths_to_product_records(records):
        return records

    def add_mask_paths_to_video_frames(frames):
        return frames

    def build_product_image_records(job_id, count=3):
        return []

    def build_products_image_ready_event(job_id, record):
        return {"job_id": job_id}

    def build_products_images_masked_batch_event(job_id, total_images):
        return {"job_id": job_id, "total_images": total_images}

    def build_products_images_ready_batch_event(job_id, total_images):
        return {"job_id": job_id, "total_images": total_images}

    def build_products_image_masked_event(job_id, record):
        return {"job_id": job_id}

    def build_video_frame_records(job_id, video_id, count=5):
        return []

    def build_video_keyframes_masked_batch_event(job_id, total_keyframes):
        return {"job_id": job_id, "total_keyframes": total_keyframes}

    def build_video_keyframes_masked_event(job_id, frame_record):
        return {"job_id": job_id}

    def build_video_record(job_id):
        return {"video_id": f"{job_id}_video_001", "platform": "youtube", "url": f"https://example.com/{job_id}.mp4"}

    def build_videos_keyframes_ready_batch_event(job_id, total_keyframes):
        return {"job_id": job_id, "total_keyframes": total_keyframes}

    def build_videos_keyframes_ready_event(job_id, video_id, frames):
        return {"job_id": job_id, "video_id": video_id, "frames": frames}


@pytest.mark.integration
@pytest.mark.feature_extraction
class TestFeatureExtractionPhase:
    """Feature Extraction Phase Integration Tests"""

    @staticmethod
    def build_product_dataset(job_id: str, count: int = 3) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Return product records and associated events for a job."""
        records = build_product_image_records(job_id, count)
        events = {
            "individual": [build_products_image_ready_event(job_id, rec) for rec in records],
            "ready_batch": build_products_images_ready_batch_event(job_id, len(records)),
            "masked_batch": build_products_images_masked_batch_event(job_id, len(records)),
        }
        return records, events

    @staticmethod
    def build_video_dataset(job_id: str, frame_count: int = 5) -> Dict[str, Any]:
        """Return video metadata, frame records, and events for a job."""
        video = build_video_record(job_id)
        frames = build_video_frame_records(job_id, video["video_id"], frame_count)
        return {
            "video": video,
            "frames": frames,
            "ready_event": build_videos_keyframes_ready_event(job_id, video["video_id"], frames),
            "ready_batch": build_videos_keyframes_ready_batch_event(job_id, len(frames)),
            "masked_batch": build_video_keypoints_masked_batch_event(job_id, len(frames)),
        }

    @staticmethod
    def prepare_masked_product_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Return product records with masked paths populated."""
        return add_mask_paths_to_product_records(records)

    @staticmethod
    def prepare_masked_video_frames(frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Return video frame records with masked paths populated."""
        return add_mask_paths_to_video_frames(frames)

    @staticmethod
    async def ensure_job(db_manager, job_id: str, phase: str = "feature_extraction", industry: str = "ergonomic pillows"):
        """Ensure a job row exists for the provided job_id."""
        await db_manager.execute(
            """
            INSERT INTO jobs (job_id, industry, phase, created_at, updated_at)
            VALUES ($1, $2, $3, NOW(), NOW())
            ON CONFLICT (job_id) DO NOTHING;
            """,
            job_id,
            industry,
            phase,
        )

    @staticmethod
    async def insert_products_and_images(db_manager, job_id: str, records: List[Dict[str, Any]]):
        """Insert product and image records for testing."""
        for record in records:
            await db_manager.execute(
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

            await db_manager.execute(
                """
                INSERT INTO product_images (img_id, product_id, local_path, created_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (img_id) DO NOTHING;
                """,
                record["img_id"],
                record["product_id"],
                record["local_path"],
            )

    @staticmethod
    async def insert_video_and_frames(db_manager, job_id: str, video: Dict[str, Any], frames: List[Dict[str, Any]]):
        """Insert video and frame records for testing."""
        await db_manager.execute(
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
            await db_manager.execute(
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
    async def feature_extraction_spy(self, message_broker):
        """Feature extraction message spy fixture"""
        spy = FeatureExtractionSpy(config.BUS_BROKER)
        await spy.connect()
        yield spy
        await spy.disconnect()

    @pytest_asyncio.fixture
    async def feature_extraction_cleanup(self, db_manager):
        """Feature extraction database cleanup fixture"""
        cleanup = FeatureExtractionCleanup(db_manager)
        await cleanup.cleanup_test_data()
        yield cleanup
        await cleanup.cleanup_test_data()

    @pytest_asyncio.fixture
    async def feature_extraction_state_validator(self, db_manager):
        """Feature extraction state validator fixture"""
        return FeatureExtractionStateValidator(db_manager)

    @pytest_asyncio.fixture
    async def feature_extraction_event_publisher(self, message_broker):
        """Feature extraction event publisher fixture"""
        publisher = FeatureExtractionEventPublisher(message_broker)
        yield publisher
        publisher.clear_published_events()

    @pytest_asyncio.fixture
    async def observability_validator(self, db_manager, message_broker):
        """Observability validator fixture"""
        from support.validators.observability_validator import ObservabilityValidator
        validator = ObservabilityValidator(db_manager, message_broker)
        yield validator
        # Clean up if needed
        if validator.is_capturing:
            validator.stop_observability_capture()
            validator.clear_all_captures()

    @pytest_asyncio.fixture
    async def feature_extraction_test_environment(
        self,
        db_manager,
        message_broker,
        feature_extraction_spy,
        feature_extraction_cleanup,
        observability_validator,
        feature_extraction_event_publisher,
        feature_extraction_state_validator
    ):
        """Complete feature extraction test environment"""
        # Clear any existing messages and ensure clean DB state
        feature_extraction_spy.clear_messages()
        await feature_extraction_cleanup.cleanup_test_data()

        # Start observability capture
        observability_validator.start_observability_capture()

        yield {
            "spy": feature_extraction_spy,
            "cleanup": feature_extraction_cleanup,
            "validator": feature_extraction_state_validator,
            "publisher": feature_extraction_event_publisher,
            "observability": observability_validator,
            "db_manager": db_manager,
            "message_broker": message_broker
        }

        # Stop capture and clean up
        try:
            observability_validator.stop_observability_capture()
            observability_validator.clear_all_captures()
        finally:
            await feature_extraction_cleanup.cleanup_test_data()
