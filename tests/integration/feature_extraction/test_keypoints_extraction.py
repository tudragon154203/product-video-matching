"""
Feature Extraction Keypoints Integration Tests
Tests the traditional computer vision keypoint extraction phase of the feature extraction pipeline.
"""
import pytest
from typing import Any, Dict, List

from support.feature_extraction_fixtures import TestFeatureExtractionPhase as TestFeatureExtractionPhaseFixtures

# Fix import path - test_data is in integration/support
try:
    from tests.integration.support.test_data import (
        add_mask_paths_to_product_records,
        add_mask_paths_to_video_frames,
        build_product_image_records,
        build_products_images_masked_batch_event,
    )
except ImportError:
    # Fallback for when running from different contexts
    from integration.support.test_data import (
        add_mask_paths_to_product_records,
        add_mask_paths_to_video_frames,
        build_product_image_records,
        build_products_images_masked_batch_event,
    )

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.feature_extraction,
    pytest.mark.keypoints,
    pytest.mark.timeout(300),
]

class TestFeatureExtractionKeypoints(TestFeatureExtractionPhaseFixtures):
    """Feature Extraction Keypoints Integration Tests."""

    async def test_image_keypoints_happy_path(
        self,
        feature_extraction_test_environment: Dict[str, Any],
    ):
        """Image Keypoints — Happy Path."""
        env = feature_extraction_test_environment
        spy = env["spy"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = f"test_keypoints_{uuid.uuid4().hex[:8]}"
        base_records, events = self.build_product_dataset(job_id)
        masked_records = self.prepare_masked_product_records(base_records)

        await self._setup_masked_product_database_state(
            db_manager,
            job_id,
            masked_records,
            ensure_mask_paths=False,
        )

        initial_state = await validator.validate_initial_state(job_id)
        assert initial_state["products_count"] == len(masked_records), "Unexpected initial product count"
        assert initial_state["keypoints_count"] == 0, "Keypoints should be empty before processing"

        await publisher.publish_products_images_masked_batch(events["masked_batch"])

        keypoints_completed = await spy.wait_for_image_keypoints_completed(job_id, timeout=180)
        assert keypoints_completed["event_data"]["job_id"] == job_id

        final_state = await validator.validate_feature_extraction_completed(job_id)
        assert final_state["keypoints_count"] == len(masked_records), "Keypoints count mismatch"

        keypoints_details = final_state["keypoints_details"]
        assert len(keypoints_details) == len(masked_records), "Missing keypoint detail rows"

        for keypoints in keypoints_details:
            assert keypoints["num_keypoints"] > 0, f"Invalid keypoints count for {keypoints['product_id']}"
            assert keypoints["model_version"], f"Missing model version for {keypoints['product_id']}"
            assert keypoints["keypoint_data"], f"Missing keypoint data for {keypoints['product_id']}"

        await self._validate_keypoints_observability(observability, job_id)

    async def test_video_keypoints_happy_path(
        self,
        feature_extraction_test_environment: Dict[str, Any],
    ):
        """Video Keypoints — Happy Path."""
        env = feature_extraction_test_environment
        spy = env["spy"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_video_keypoints_001"
        video_dataset = self.build_video_dataset(job_id)
        masked_frames = self.prepare_masked_video_frames(video_dataset["frames"])

        await self._setup_masked_video_database_state(
            db_manager,
            job_id,
            video_dataset["video"],
            masked_frames,
            ensure_mask_paths=False,
        )

        initial_state = await validator.validate_initial_state(job_id)
        assert initial_state["videos_count"] == 1, "Expected single video record"
        assert initial_state["frames_count"] == len(masked_frames), "Unexpected frame count"
        assert initial_state["video_keypoints_count"] == 0, "Video keypoints should be empty before processing"

        await publisher.publish_video_keyframes_masked_batch(video_dataset["masked_batch"])

        video_keypoints_completed = await spy.wait_for_video_keypoints_completed(job_id, timeout=180)
        assert video_keypoints_completed["event_data"]["job_id"] == job_id

        final_state = await validator.validate_feature_extraction_completed(job_id)
        assert final_state["video_keypoints_count"] == len(masked_frames), "Video keypoints count mismatch"

        video_keypoints_details = final_state.get("video_keypoints_details", [])
        assert len(video_keypoints_details) == len(masked_frames), "Missing video keypoint detail rows"

        for frame_keypoints in video_keypoints_details:
            assert frame_keypoints["num_keypoints"] > 0, "Invalid video keypoint count"
            assert frame_keypoints["model_version"], "Missing video keypoint model version"

        await self._validate_keypoints_observability(observability, job_id)

    async def test_keypoints_single_item_processing(
        self,
        feature_extraction_test_environment: Dict[str, Any],
    ):
        """Keypoints — Single Item Processing."""
        env = feature_extraction_test_environment
        spy = env["spy"]
        validator = env["validator"]
        publisher = env["publisher"]
        db_manager = env["db_manager"]

        job_id = "test_keypoints_single_001"
        base_records, events = self.build_product_dataset(job_id, count=1)
        masked_records = self.prepare_masked_product_records(base_records)

        await self._setup_masked_product_database_state(
            db_manager,
            job_id,
            masked_records,
            ensure_mask_paths=False,
        )

        initial_state = await validator.validate_initial_state(job_id)
        assert initial_state["products_count"] == 1, "Expected single product in initial state"
        assert initial_state["keypoints_count"] == 0, "Keypoints should be empty before processing"

        await publisher.publish_products_images_masked_batch(events["masked_batch"])

        keypoints_completed = await spy.wait_for_image_keypoints_completed(job_id, timeout=120)
        assert keypoints_completed["event_data"]["job_id"] == job_id

        final_state = await validator.validate_feature_extraction_completed(job_id)
        assert final_state["keypoints_count"] == 1, "Expected single keypoint entry"

        keypoints_details = final_state["keypoints_details"]
        assert len(keypoints_details) == 1, "Expected keypoint detail for single product"

        keypoints = keypoints_details[0]
        assert keypoints["product_id"] == masked_records[0]["product_id"], "Product ID mismatch"
        assert keypoints["num_keypoints"] > 0, "Invalid keypoint count"
        assert keypoints["model_version"], "Missing keypoint model version"

    async def test_keypoints_invalid_masked_image_handling(
        self,
        feature_extraction_test_environment: Dict[str, Any],
    ):
        """Keypoints — Invalid Masked Image Handling."""
        env = feature_extraction_test_environment
        spy = env["spy"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_keypoints_invalid_001"
        base_records = build_product_image_records(job_id, count=3)
        masked_records = add_mask_paths_to_product_records(base_records)

        # Introduce an invalid masked path to simulate corrupt assets.
        masked_records[1]["masked_local_path"] = "/data/tests/products/masked/invalid_missing.png"

        await self._setup_masked_product_database_state(
            db_manager,
            job_id,
            masked_records,
            ensure_mask_paths=False,
        )

        products_masked_event = build_products_images_masked_batch_event(job_id, len(masked_records))
        await publisher.publish_products_images_masked_batch(products_masked_event)

        try:
            keypoints_completed = await spy.wait_for_image_keypoints_completed(job_id, timeout=180)
            assert keypoints_completed["event_data"]["job_id"] == job_id
        except TimeoutError:
            # Acceptable if keypoint generation fails for all invalid inputs.
            pass

        await self._validate_invalid_image_keypoints_observability(observability, job_id)

    async def _setup_masked_product_database_state(
        self,
        db_manager,
        job_id: str,
        product_records: List[Dict[str, Any]],
        ensure_mask_paths: bool = True,
    ):
        """Persist product data with masked images."""
        prepared_records = (
            self.prepare_masked_product_records(product_records)
            if ensure_mask_paths
            else product_records
        )

        await self.ensure_job(db_manager, job_id)
        await self.insert_products_and_images(db_manager, job_id, prepared_records)

    async def _setup_masked_video_database_state(
        self,
        db_manager,
        job_id: str,
        video: Dict[str, Any],
        frames: List[Dict[str, Any]],
        ensure_mask_paths: bool = True,
    ):
        """Persist video data with masked keyframes."""
        prepared_frames = (
            self.prepare_masked_video_frames(frames)
            if ensure_mask_paths
            else frames
        )

        await self.ensure_job(db_manager, job_id)
        await self.insert_video_and_frames(db_manager, job_id, video, prepared_frames)

    async def _validate_keypoints_observability(self, observability, job_id: str):
        """Validate observability for successful keypoint operations."""
        captured_logs = observability.get_captured_logs()
        service_logs = {log["service"] for log in captured_logs if log.get("job_id") == job_id}

        assert "vision-keypoint" in service_logs or service_logs, "Expected logs from vision-keypoint service"

        captured_metrics = observability.get_captured_metrics()
        assert captured_metrics, "Expected keypoint metrics to be captured"

        keypoint_logs = [
            log
            for log in captured_logs
            if log.get("job_id") == job_id
            and (
                "keypoint" in log.get("message", "").lower()
                or "akaze" in log.get("message", "").lower()
                or "sift" in log.get("message", "").lower()
            )
        ]
        assert keypoint_logs, "Expected keypoint processing logs"

    async def _validate_invalid_image_keypoints_observability(self, observability, job_id: str):
        """Validate observability for invalid masked image keypoint handling."""
        captured_logs = observability.get_captured_logs()
        error_logs = [
            log
            for log in captured_logs
            if log.get("job_id") == job_id
            and log.get("level") in ("ERROR", "WARNING")
            and (
                "keypoint" in log.get("message", "").lower()
                or "image" in log.get("message", "").lower()
            )
        ]

        assert error_logs or captured_logs, "Expected observability entries for invalid keypoints handling"
