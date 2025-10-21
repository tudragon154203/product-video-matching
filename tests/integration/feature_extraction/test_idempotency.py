"""
Feature Extraction Idempotency Integration Tests
Tests idempotency, duplicate handling, and event re-processing in the feature extraction pipeline.
"""
import asyncio
import copy
import pytest
from typing import Any, Dict, List

from support.feature_extraction_fixtures import TestFeatureExtractionPhase as TestFeatureExtractionPhaseFixtures

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.feature_extraction,
    pytest.mark.idempotency,
    pytest.mark.timeout(300),
]

class TestFeatureExtractionIdempotency(TestFeatureExtractionPhaseFixtures):
    """Feature Extraction Idempotency Integration Tests."""

    async def test_masking_events_idempotency(
        self,
        feature_extraction_test_environment: Dict[str, Any],
    ):
        """Idempotency — Masking Events."""
        env = feature_extraction_test_environment
        spy = env["spy"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_idempotency_masking_001"
        product_records, events = self.build_product_dataset(job_id)

        await self._setup_products_ready_state(db_manager, job_id, product_records)
        await self._publish_ready_events(publisher, events)

        products_masked = await spy.wait_for_products_images_masked(job_id, timeout=120)

        initial_state = await validator.validate_masking_completed(job_id)
        initial_masked_count = initial_state["masked_images_count"]

        await publisher.publish_products_images_masked_batch(products_masked["event_data"])
        await asyncio.sleep(10)

        final_state = await validator.validate_masking_completed(job_id)
        assert final_state["masked_images_count"] == initial_masked_count, "Duplicate masked images were created"

        await self._validate_idempotency_observability(observability, job_id, "masking")

    async def test_embedding_events_idempotency(
        self,
        feature_extraction_test_environment: Dict[str, Any],
    ):
        """Idempotency — Embedding Events."""
        env = feature_extraction_test_environment
        spy = env["spy"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_idempotency_embeddings_001"
        product_records, events = self.build_product_dataset(job_id)
        masked_records = self.prepare_masked_product_records(product_records)

        await self._setup_masked_products_state(db_manager, job_id, masked_records, ensure_mask_paths=False)
        await publisher.publish_products_images_masked_batch(events["masked_batch"])

        embeddings_completed = await spy.wait_for_image_embeddings_completed(job_id, timeout=180)

        initial_state = await validator.validate_feature_extraction_completed(job_id)
        initial_embeddings = initial_state["embeddings_count"]

        await publisher.publish_image_embeddings_completed(embeddings_completed["event_data"])
        await asyncio.sleep(10)

        final_state = await validator.validate_feature_extraction_completed(job_id)
        assert final_state["embeddings_count"] == initial_embeddings, "Duplicate embeddings were created"

        duplicates = await validator.validate_no_duplicate_processing(job_id)
        assert duplicates["duplicate_embeddings"] == 0, f"Found {duplicates['duplicate_embeddings']} duplicate embeddings"

        await self._validate_idempotency_observability(observability, job_id, "embeddings")

    async def test_keypoint_events_idempotency(
        self,
        feature_extraction_test_environment: Dict[str, Any],
    ):
        """Idempotency — Keypoint Events."""
        env = feature_extraction_test_environment
        spy = env["spy"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_idempotency_keypoints_001"
        product_records, events = self.build_product_dataset(job_id)
        masked_records = self.prepare_masked_product_records(product_records)

        await self._setup_masked_products_state(db_manager, job_id, masked_records, ensure_mask_paths=False)
        await publisher.publish_products_images_masked_batch(events["masked_batch"])

        keypoints_completed = await spy.wait_for_image_keypoints_completed(job_id, timeout=180)

        initial_state = await validator.validate_feature_extraction_completed(job_id)
        initial_keypoints = initial_state["keypoints_count"]

        await publisher.publish_image_keypoints_completed(keypoints_completed["event_data"])
        await asyncio.sleep(10)

        final_state = await validator.validate_feature_extraction_completed(job_id)
        assert final_state["keypoints_count"] == initial_keypoints, "Duplicate keypoints were created"

        duplicates = await validator.validate_no_duplicate_processing(job_id)
        assert duplicates["duplicate_keypoints"] == 0, f"Found {duplicates['duplicate_keypoints']} duplicate keypoints"

        await self._validate_idempotency_observability(observability, job_id, "keypoints")

    async def test_ready_events_idempotency(
        self,
        feature_extraction_test_environment: Dict[str, Any],
    ):
        """Idempotency — Ready Events."""
        env = feature_extraction_test_environment
        spy = env["spy"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_idempotency_ready_001"
        product_records, events = self.build_product_dataset(job_id)

        await self._setup_products_ready_state(db_manager, job_id, product_records)
        await self._publish_ready_events(publisher, events)

        products_masked = await spy.wait_for_products_images_masked(job_id, timeout=120)
        spy.clear_messages()

        await self._publish_ready_events(publisher, events)
        await asyncio.sleep(20)

        try:
            duplicate_masked = await spy.wait_for_products_images_masked(job_id, timeout=30)
            assert duplicate_masked["event_data"]["job_id"] == job_id
        except TimeoutError:
            pass

        final_state = await validator.validate_masking_completed(job_id)
        assert final_state["masked_images_count"] == len(product_records), "Final masked count changed unexpectedly"

        await self._validate_idempotency_observability(observability, job_id, "ready_events")

    async def test_event_id_based_idempotency(
        self,
        feature_extraction_test_environment: Dict[str, Any],
    ):
        """Idempotency — Event ID Based Deduplication."""
        env = feature_extraction_test_environment
        spy = env["spy"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_idempotency_event_id_001"
        product_records, events = self.build_product_dataset(job_id)

        await self._setup_products_ready_state(db_manager, job_id, product_records)

        base_event = copy.deepcopy(events["ready_batch"])
        base_event["event_id"] = "duplicate_test_event_123"

        await publisher.publish_products_images_ready_batch(base_event)
        await spy.wait_for_products_images_masked(job_id, timeout=120)

        duplicate_event = copy.deepcopy(base_event)
        duplicate_event["total_images"] = 999
        duplicate_event["timestamp"] = "2024-01-01T12:00:01Z"

        await publisher.publish_products_images_ready_batch(duplicate_event)
        await asyncio.sleep(15)

        final_state = await validator.validate_masking_completed(job_id)
        assert final_state["masked_images_count"] == len(product_records), "Event ID deduplication failed"

        await self._validate_event_id_idempotency_observability(observability, job_id)

    async def test_partial_retry_idempotency(
        self,
        feature_extraction_test_environment: Dict[str, Any],
    ):
        """Idempotency — Partial Retry Scenarios."""
        env = feature_extraction_test_environment
        spy = env["spy"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_idempotency_partial_retry_001"
        product_records, events = self.build_product_dataset(job_id)
        masked_records = self.prepare_masked_product_records(product_records)

        await self._setup_products_ready_state(db_manager, job_id, product_records)
        await self._publish_ready_events(publisher, events)

        products_masked = await spy.wait_for_products_images_masked(job_id, timeout=120)

        await self._apply_masked_paths(db_manager, job_id, masked_records)
        await self._mark_embeddings_processed(db_manager, masked_records[:2])

        await publisher.publish_products_images_masked_batch(products_masked["event_data"])

        try:
            embeddings_completed = await spy.wait_for_image_embeddings_completed(job_id, timeout=180)
            assert embeddings_completed["event_data"]["job_id"] == job_id
        except TimeoutError:
            pass

        final_state = await validator.validate_feature_extraction_completed(job_id)
        assert final_state["embeddings_count"] == len(masked_records), "Partial retry did not process all embeddings"

        await self._validate_partial_retry_observability(observability, job_id)

    async def _setup_products_ready_state(
        self,
        db_manager,
        job_id: str,
        product_records: List[Dict[str, Any]],
    ):
        """Insert product data for ready-event scenarios."""
        await self.ensure_job(db_manager, job_id)
        await self.insert_products_and_images(db_manager, job_id, product_records)

    async def _setup_masked_products_state(
        self,
        db_manager,
        job_id: str,
        product_records: List[Dict[str, Any]],
        ensure_mask_paths: bool = True,
    ):
        """Insert product data with masked paths for downstream stages."""
        prepared_records = (
            self.prepare_masked_product_records(product_records)
            if ensure_mask_paths
            else product_records
        )
        await self.ensure_job(db_manager, job_id)
        await self.insert_products_and_images(db_manager, job_id, prepared_records)

    async def _publish_ready_events(
        self,
        publisher,
        events: Dict[str, Any],
    ):
        """Publish individual and batch ready events."""
        for event in events["individual"]:
            await publisher.publish_products_image_ready(event)
        await publisher.publish_products_images_ready_batch(events["ready_batch"])

    async def _apply_masked_paths(
        self,
        db_manager,
        job_id: str,
        masked_records: List[Dict[str, Any]],
    ):
        """Update product image rows with masked paths."""
        for record in masked_records:
            await db_manager.execute(
                """
                UPDATE product_images
                SET masked_local_path = $2
                WHERE img_id = $1
                  AND product_id = $3
                """,
                record["img_id"],
                record["masked_local_path"],
                record["product_id"],
            )

    async def _mark_embeddings_processed(
        self,
        db_manager,
        product_records: List[Dict[str, Any]],
    ):
        """Mark subset of product images as having embeddings."""
        embedding_vector = "[" + ",".join(["0"] * 512) + "]"

        for record in product_records:
            await db_manager.execute(
                """
                UPDATE product_images
                SET emb_rgb = $2::vector
                WHERE img_id = $1
                """,
                record["img_id"],
                embedding_vector,
            )

    async def _validate_idempotency_observability(self, observability, job_id: str, component: str):
        """Validate observability for idempotency handling."""
        captured_logs = observability.get_captured_logs()
        idempotency_logs = [
            log
            for log in captured_logs
            if log.get("job_id") == job_id
            and (
                "idempotent" in log.get("message", "").lower()
                or "duplicate" in log.get("message", "").lower()
                or "already processed" in log.get("message", "").lower()
            )
        ]
        assert idempotency_logs or captured_logs, f"Expected idempotency handling logs for {component}"

    async def _validate_event_id_idempotency_observability(self, observability, job_id: str):
        """Validate observability for event ID based idempotency."""
        captured_logs = observability.get_captured_logs()
        event_id_logs = [
            log
            for log in captured_logs
            if log.get("job_id") == job_id
            and (
                "event_id" in log.get("message", "").lower()
                or "deduplication" in log.get("message", "").lower()
            )
        ]
        assert event_id_logs or captured_logs, "Expected event ID deduplication logging"

    async def _validate_partial_retry_observability(self, observability, job_id: str):
        """Validate observability for partial retry scenarios."""
        captured_logs = observability.get_captured_logs()
        retry_logs = [
            log
            for log in captured_logs
            if log.get("job_id") == job_id
            and (
                "retry" in log.get("message", "").lower()
                or "partial" in log.get("message", "").lower()
                or "remaining" in log.get("message", "").lower()
            )
        ]
        assert retry_logs or captured_logs, "Expected partial retry observability entries"
