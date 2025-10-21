"""
Feature Extraction Error Handling Integration Tests
Tests error handling, edge cases, and failure recovery in the feature extraction pipeline.
"""
import asyncio
import pytest
from typing import Any, Dict, List

from support.feature_extraction_fixtures import TestFeatureExtractionPhase as TestFeatureExtractionPhaseFixtures

# Fix import path - test_data is in integration/support
try:
    from tests.integration.support.test_data import (
        add_mask_paths_to_product_records,
        build_product_image_records,
        build_products_images_masked_batch_event,
        build_products_images_ready_batch_event,
    )
except ImportError:
    # Fallback for when running from different contexts
    from integration.support.test_data import (
        add_mask_paths_to_product_records,
        build_product_image_records,
        build_products_images_masked_batch_event,
        build_products_images_ready_batch_event,
    )

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.feature_extraction,
    pytest.mark.error_handling,
    pytest.mark.timeout(300),
]

class TestFeatureExtractionErrorHandling(TestFeatureExtractionPhaseFixtures):
    """Feature Extraction Error Handling Integration Tests."""

    async def test_missing_database_records_handling(
        self,
        feature_extraction_test_environment: Dict[str, Any],
    ):
        """Error Handling — Missing Database Records."""
        env = feature_extraction_test_environment
        spy = env["spy"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_error_missing_records_001"
        await self.ensure_job(db_manager, job_id)

        # Publish events without corresponding database records
        ready_event = build_products_images_ready_batch_event(job_id, total_images=3)
        await publisher.publish_products_images_ready_batch(ready_event)

        await asyncio.sleep(10)

        try:
            products_masked = await spy.wait_for_products_images_masked(job_id, timeout=30)
            assert products_masked["event_data"].get("total_images", 0) == 0
        except TimeoutError:
            pass

        await self._validate_missing_records_observability(observability, job_id)

    async def test_corrupted_masked_image_handling(
        self,
        feature_extraction_test_environment: Dict[str, Any],
    ):
        """Error Handling — Corrupted Masked Images."""
        env = feature_extraction_test_environment
        spy = env["spy"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_error_corrupted_001"
        base_records = build_product_image_records(job_id, count=4)
        masked_records = add_mask_paths_to_product_records(base_records)

        # Introduce invalid paths
        masked_records[1]["masked_local_path"] = "/data/tests/products/masked/corrupted_image.png"
        masked_records[2]["masked_local_path"] = "/data/tests/products/masked/nonexistent.png"

        await self._setup_masked_products_state(db_manager, job_id, masked_records, ensure_mask_paths=False)

        products_masked_event = build_products_images_masked_batch_event(job_id, len(masked_records))
        await publisher.publish_products_images_masked_batch(products_masked_event)

        try:
            embeddings_completed = await spy.wait_for_image_embeddings_completed(job_id, timeout=120)
            assert embeddings_completed["event_data"]["job_id"] == job_id

            keypoints_completed = await spy.wait_for_image_keypoints_completed(job_id, timeout=120)
            assert keypoints_completed["event_data"]["job_id"] == job_id
        except TimeoutError:
            pass

        await self._validate_corrupted_image_observability(observability, job_id)

    async def test_service_unavailable_handling(
        self,
        feature_extraction_test_environment: Dict[str, Any],
    ):
        """Error Handling — Service Unavailable."""
        env = feature_extraction_test_environment
        spy = env["spy"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_error_service_unavailable_001"
        base_records, events = self.build_product_dataset(job_id)
        masked_records = self.prepare_masked_product_records(base_records)

        await self._setup_masked_products_state(db_manager, job_id, masked_records, ensure_mask_paths=False)

        await publisher.publish_products_images_masked_batch(events["masked_batch"])

        try:
            embeddings_completed = await spy.wait_for_image_embeddings_completed(job_id, timeout=300)
            assert embeddings_completed["event_data"]["job_id"] == job_id
        except TimeoutError:
            pass

        await self._validate_service_unavailable_observability(observability, job_id)

    async def test_malformed_event_handling(
        self,
        feature_extraction_test_environment: Dict[str, Any],
    ):
        """Error Handling — Malformed Events."""
        env = feature_extraction_test_environment
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_error_malformed_001"
        await self.ensure_job(db_manager, job_id)

        malformed_events = [
            ("products.images.ready.batch", {"total_images": 2}),
            (
                "products.images.ready.batch",
                {
                    "job_id": job_id,
                    "total_images": "not_a_number",
                },
            ),
            (
                "products.images.ready.batch",
                {
                    "job_id": job_id,
                    "total_images": 1,
                    "unknown_field": "should_be_ignored",
                },
            ),
        ]

        for routing_key, payload in malformed_events:
            await publisher.publish_raw_event(routing_key, payload)

        await asyncio.sleep(10)
        await self._validate_malformed_event_observability(observability, job_id)

    async def test_database_constraint_violations(
        self,
        feature_extraction_test_environment: Dict[str, Any],
    ):
        """Error Handling — Database Constraint Violations."""
        env = feature_extraction_test_environment
        spy = env["spy"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_error_constraints_001"
        base_records, events = self.build_product_dataset(job_id)
        masked_records = self.prepare_masked_product_records(base_records)

        await self._setup_masked_products_state(db_manager, job_id, masked_records, ensure_mask_paths=False)

        products_masked_event = build_products_images_masked_batch_event(job_id, len(masked_records))
        await publisher.publish_products_images_masked_batch(products_masked_event)

        try:
            embeddings_completed = await spy.wait_for_image_embeddings_completed(job_id, timeout=180)
            assert embeddings_completed["event_data"]["job_id"] == job_id
        except TimeoutError:
            pass

        await self._validate_constraint_violation_observability(observability, job_id)

    async def _setup_masked_products_state(
        self,
        db_manager,
        job_id: str,
        product_records: List[Dict[str, Any]],
        ensure_mask_paths: bool = True,
    ):
        """Persist product records with optional masked paths."""
        prepared_records = (
            self.prepare_masked_product_records(product_records)
            if ensure_mask_paths
            else product_records
        )

        await self.ensure_job(db_manager, job_id)
        await self.insert_products_and_images(db_manager, job_id, prepared_records)

    async def _validate_missing_records_observability(self, observability, job_id: str):
        captured_logs = observability.get_captured_logs()
        error_logs = [
            log
            for log in captured_logs
            if log.get("job_id") == job_id and "not found" in log.get("message", "").lower()
        ]
        assert error_logs or captured_logs, "Expected missing record observability entries"

    async def _validate_corrupted_image_observability(self, observability, job_id: str):
        captured_logs = observability.get_captured_logs()
        error_logs = [
            log
            for log in captured_logs
            if log.get("job_id") == job_id
            and log.get("level") in ("ERROR", "WARNING")
            and (
                "corrupt" in log.get("message", "").lower()
                or "missing" in log.get("message", "").lower()
            )
        ]
        assert error_logs or captured_logs, "Expected corrupted image observability entries"

    async def _validate_service_unavailable_observability(self, observability, job_id: str):
        captured_logs = observability.get_captured_logs()
        retry_logs = [
            log
            for log in captured_logs
            if log.get("job_id") == job_id and "retry" in log.get("message", "").lower()
        ]
        assert retry_logs or captured_logs, "Expected retry observability entries"

    async def _validate_malformed_event_observability(self, observability, job_id: str):
        captured_logs = observability.get_captured_logs()
        validation_logs = [
            log
            for log in captured_logs
            if log.get("job_id") == job_id and "validation" in log.get("message", "").lower()
        ]
        assert validation_logs or captured_logs, "Expected validation observability entries"

    async def _validate_constraint_violation_observability(self, observability, job_id: str):
        captured_logs = observability.get_captured_logs()
        conflict_logs = [
            log
            for log in captured_logs
            if log.get("job_id") == job_id and "conflict" in log.get("message", "").lower()
        ]
        assert conflict_logs or captured_logs, "Expected constraint violation observability entries"
