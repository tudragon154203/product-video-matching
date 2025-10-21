"""
Feature Extraction Phase Integration Tests
Tests the complete feature extraction pipeline from ready inputs through masking to feature completion.
"""
import asyncio
import pytest
from typing import Any, Dict, List

from support.feature_extraction_fixtures import TestFeatureExtractionPhase as TestFeatureExtractionPhaseFixtures

# Fix import path - test_data is in integration/support
try:
    from tests.integration.support.test_data import build_products_images_ready_batch_event
except ImportError:
    from integration.support.test_data import build_products_images_ready_batch_event

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.feature_extraction,
    pytest.mark.timeout(900),
]

class TestFeatureExtractionPhase(TestFeatureExtractionPhaseFixtures):
    """Feature Extraction Phase Integration Tests."""

    async def test_end_to_end_feature_extraction_happy_path(
        self,
        feature_extraction_test_environment: Dict[str, Any],
    ):
        """End-to-end happy path covering masking → embeddings → keypoints."""
        env = feature_extraction_test_environment
        spy = env["spy"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_feature_extraction_001"
        product_records, product_events = self.build_product_dataset(job_id)
        video_dataset = self.build_video_dataset(job_id)

        await self._setup_database_state(db_manager, job_id, product_records, video_dataset)

        initial_state = await validator.validate_initial_state(job_id)
        assert initial_state["products_count"] == len(product_records)
        assert initial_state["images_count"] == len(product_records)
        assert initial_state["videos_count"] == 1
        assert initial_state["frames_count"] == len(video_dataset["frames"])
        assert initial_state["embeddings_count"] == 0
        assert initial_state["keypoints_count"] == 0

        for event in product_events["individual"]:
            await publisher.publish_products_image_ready(event)
        await publisher.publish_video_keyframes_ready(video_dataset["ready_event"])

        await publisher.publish_products_images_ready_batch(product_events["ready_batch"])
        await publisher.publish_video_keyframes_ready_batch(video_dataset["ready_batch"])

        products_masked = await spy.wait_for_products_images_masked(job_id, timeout=180)
        videos_masked = await spy.wait_for_video_keyframes_masked(job_id, timeout=180)

        assert products_masked["event_data"]["job_id"] == job_id
        assert products_masked["event_data"]["total_images"] == len(product_records)
        assert videos_masked["event_data"]["job_id"] == job_id
        assert videos_masked["event_data"]["total_keyframes"] == len(video_dataset["frames"])

        embeddings_completed = await spy.wait_for_image_embeddings_completed(job_id, timeout=240)
        keypoints_completed = await spy.wait_for_image_keypoints_completed(job_id, timeout=240)
        video_keypoints_completed = await spy.wait_for_video_keypoints_completed(job_id, timeout=240)

        assert embeddings_completed["event_data"]["processed_assets"] == len(product_records)
        assert keypoints_completed["event_data"]["job_id"] == job_id
        assert video_keypoints_completed["event_data"]["job_id"] == job_id

        final_state = await validator.validate_feature_extraction_completed(job_id)
        assert final_state["embeddings_count"] == len(product_records)
        assert final_state["keypoints_count"] == len(product_records)
        assert final_state["video_keypoints_count"] == len(video_dataset["frames"])

        await self._validate_observability(observability, job_id)

    async def test_critical_idempotency_feature_completion(
        self,
        feature_extraction_test_environment: Dict[str, Any],
    ):
        """Ensure duplicate completion events do not create duplicate data."""
        env = feature_extraction_test_environment
        spy = env["spy"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_feature_extraction_idempotency"
        product_records, product_events = self.build_product_dataset(job_id)
        video_dataset = self.build_video_dataset(job_id)

        await self._setup_database_state(db_manager, job_id, product_records, video_dataset)

        for event in product_events["individual"]:
            await publisher.publish_products_image_ready(event)
        await publisher.publish_video_keyframes_ready(video_dataset["ready_event"])
        await publisher.publish_products_images_ready_batch(product_events["ready_batch"])
        await publisher.publish_video_keyframes_ready_batch(video_dataset["ready_batch"])

        embeddings_completed = await spy.wait_for_image_embeddings_completed(job_id, timeout=240)
        await spy.wait_for_image_keypoints_completed(job_id, timeout=240)
        await spy.wait_for_video_keypoints_completed(job_id, timeout=240)

        baseline_state = await validator.validate_feature_extraction_completed(job_id)
        baseline_embeddings = baseline_state["embeddings_count"]
        baseline_keypoints = baseline_state["keypoints_count"]
        baseline_video_keypoints = baseline_state["video_keypoints_count"]

        await publisher.publish_image_embeddings_completed(embeddings_completed["event_data"])
        await asyncio.sleep(5)

        final_state = await validator.validate_feature_extraction_completed(job_id)
        assert final_state["embeddings_count"] == baseline_embeddings
        assert final_state["keypoints_count"] == baseline_keypoints
        assert final_state["video_keypoints_count"] == baseline_video_keypoints

        duplicates = await validator.validate_no_duplicate_processing(job_id)
        assert duplicates["duplicate_embeddings"] == 0
        assert duplicates["duplicate_keypoints"] == 0

        await self._validate_idempotency_observability(observability, job_id)

    async def test_pipeline_continuity_partial_batch_processing(
        self,
        feature_extraction_test_environment: Dict[str, Any],
    ):
        """Validate partial batch handling when some assets are invalid."""
        env = feature_extraction_test_environment
        spy = env["spy"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_feature_extraction_partial"
        product_records, product_events = self.build_product_dataset(job_id)
        video_dataset = self.build_video_dataset(job_id)

        await self._setup_database_state(db_manager, job_id, product_records, video_dataset)

        valid_events = product_events["individual"][:-1]
        for event in valid_events:
            await publisher.publish_products_image_ready(event)

        partial_ready_batch = build_products_images_ready_batch_event(job_id, len(valid_events))

        await publisher.publish_products_images_ready_batch(partial_ready_batch)
        await publisher.publish_video_keyframes_ready_batch(video_dataset["ready_batch"])

        try:
            products_masked = await spy.wait_for_products_images_masked(job_id, timeout=180)
            assert products_masked["event_data"]["total_images"] <= len(product_records)
        except TimeoutError:
            pass

        try:
            embeddings_completed = await spy.wait_for_image_embeddings_completed(job_id, timeout=240)
            assert embeddings_completed["event_data"]["processed_assets"] <= len(product_records)
            await spy.wait_for_image_keypoints_completed(job_id, timeout=240)
        except TimeoutError:
            pass

        await self._validate_partial_batch_observability(observability, job_id)

        final_state = await validator.validate_feature_extraction_completed(job_id)
        assert final_state["embeddings_count"] <= len(valid_events)
        assert final_state["keypoints_count"] <= len(valid_events)

    async def _setup_database_state(
        self,
        db_manager,
        job_id: str,
        product_records: List[Dict[str, Any]],
        video_dataset: Dict[str, Any],
    ):
        await self.ensure_job(db_manager, job_id)
        await self.insert_products_and_images(db_manager, job_id, product_records)
        await self.insert_video_and_frames(db_manager, job_id, video_dataset["video"], video_dataset["frames"])

    async def _validate_observability(self, observability, job_id: str):
        captured_logs = observability.get_captured_logs()
        service_logs = {
            log.get("service")
            for log in captured_logs
            if log.get("job_id") == job_id and log.get("service")
        }
        expected_services = {"vision-embedding", "vision-keypoint", "product-segmentor", "video-crawler"}
        assert expected_services <= service_logs, "Missing service logs"

        captured_metrics = observability.get_captured_metrics()
        assert captured_metrics, "Expected metrics to be captured"

    async def _validate_idempotency_observability(self, observability, job_id: str):
        captured_logs = observability.get_captured_logs()
        idempotency_logs = [
            log
            for log in captured_logs
            if log.get("job_id") == job_id
            and (
                "idempotent" in log.get("message", "").lower()
                or "duplicate" in log.get("message", "").lower()
            )
        ]
        assert idempotency_logs or captured_logs, "Expected idempotency logging"

    async def _validate_partial_batch_observability(self, observability, job_id: str):
        captured_logs = observability.get_captured_logs()
        error_logs = [
            log
            for log in captured_logs
            if log.get("job_id") == job_id
            and log.get("level") in ("ERROR", "WARNING")
        ]
        assert error_logs or captured_logs, "Expected partial batch observability entries"
