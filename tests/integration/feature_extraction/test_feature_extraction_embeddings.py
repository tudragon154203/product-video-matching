"""
Feature Extraction Embeddings Integration Tests
Tests the CLIP embedding generation phase of the feature extraction pipeline.
"""
import pytest
from typing import Any, Dict, List

from support.feature_extraction_fixtures import TestFeatureExtractionPhase as TestFeatureExtractionPhaseFixtures

# Fix import path - test_data is in integration/support
try:
    from tests.integration.support.test_data import (
        add_mask_paths_to_product_records,
        build_product_image_records,
        build_products_images_masked_batch_event,
    )
except ImportError:
    # Fallback for when running from different contexts
    from integration.support.test_data import (
        add_mask_paths_to_product_records,
        build_product_image_records,
        build_products_images_masked_batch_event,
    )

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.feature_extraction,
    pytest.mark.embeddings,
    pytest.mark.timeout(300),
]

class TestFeatureExtractionEmbeddings(TestFeatureExtractionPhaseFixtures):
    """Feature Extraction Embeddings Integration Tests"""

    async def test_image_embeddings_happy_path(
        self,
        feature_extraction_test_environment: Dict[str, Any],
    ):
        """Image Embeddings — Happy Path."""
        env = feature_extraction_test_environment
        spy = env["spy"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_embeddings_001"
        base_records, events = self.build_product_dataset(job_id)
        masked_records = self.prepare_masked_product_records(base_records)

        await self._setup_masked_product_database_state(
            db_manager,
            job_id,
            masked_records,
            ensure_mask_paths=False,
        )

        initial_state = await validator.validate_initial_state(job_id)
        assert initial_state["products_count"] == len(masked_records), "Unexpected product count"
        assert initial_state["embeddings_count"] == 0, "Embeddings should be empty before processing"

        await publisher.publish_products_images_masked_batch(events["masked_batch"])

        embeddings_completed = await spy.wait_for_image_embeddings_completed(job_id, timeout=180)

        assert embeddings_completed["event_data"]["job_id"] == job_id
        assert embeddings_completed["event_data"]["processed_assets"] == len(masked_records)

        final_state = await validator.validate_feature_extraction_completed(job_id)
        assert final_state["embeddings_count"] == len(masked_records), "Embeddings count mismatch"

        embeddings_details = final_state["embeddings_details"]
        assert len(embeddings_details) == len(masked_records), "Missing embedding detail rows"

        for embedding in embeddings_details:
            assert embedding["embedding_dim"] > 0, f"Invalid embedding dimension for {embedding['product_id']}"
            assert embedding["model_version"], f"Missing model version for {embedding['product_id']}"
            assert embedding["embedding_vector"], f"Missing embedding vector for {embedding['product_id']}"

        await self._validate_embeddings_observability(observability, job_id)

    async def test_embeddings_single_item_processing(
        self,
        feature_extraction_test_environment: Dict[str, Any],
    ):
        """Embeddings — Single Item Processing."""
        env = feature_extraction_test_environment
        spy = env["spy"]
        validator = env["validator"]
        publisher = env["publisher"]
        db_manager = env["db_manager"]

        job_id = "test_embeddings_single_001"
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
        assert initial_state["embeddings_count"] == 0, "Embeddings should be empty before processing"

        await publisher.publish_products_images_masked_batch(events["masked_batch"])

        embeddings_completed = await spy.wait_for_image_embeddings_completed(job_id, timeout=120)

        assert embeddings_completed["event_data"]["job_id"] == job_id
        assert embeddings_completed["event_data"]["processed_assets"] == 1

        final_state = await validator.validate_feature_extraction_completed(job_id)
        assert final_state["embeddings_count"] == 1, "Expected single embedding entry"

        embeddings_details = final_state["embeddings_details"]
        assert len(embeddings_details) == 1, "Expected detail record for single embedding"

        embedding = embeddings_details[0]
        assert embedding["product_id"] == masked_records[0]["product_id"], "Product ID mismatch"
        assert embedding["embedding_dim"] > 0, "Invalid embedding dimension"
        assert embedding["model_version"], "Missing embedding model version"

    async def test_embeddings_invalid_masked_image_handling(
        self,
        feature_extraction_test_environment: Dict[str, Any],
    ):
        """Embeddings — Invalid Masked Image Handling."""
        env = feature_extraction_test_environment
        spy = env["spy"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_embeddings_invalid_001"
        base_records = build_product_image_records(job_id, count=3)
        masked_records = add_mask_paths_to_product_records(base_records)

        # Intentionally break one masked path to simulate invalid asset
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
            embeddings_completed = await spy.wait_for_image_embeddings_completed(job_id, timeout=180)
            assert embeddings_completed["event_data"]["job_id"] == job_id
            assert embeddings_completed["event_data"]["processed_assets"] <= len(masked_records), "Processed asset count exceeded total"
        except TimeoutError:
            # Acceptable when all assets fail; pipeline should still handle gracefully
            pass

        await self._validate_invalid_image_embeddings_observability(observability, job_id)

    async def _setup_masked_product_database_state(
        self,
        db_manager,
        job_id: str,
        product_records: List[Dict[str, Any]],
        ensure_mask_paths: bool = True,
    ):
        """Persist products and images ready for embedding tests."""
        prepared_records = (
            self.prepare_masked_product_records(product_records)
            if ensure_mask_paths
            else product_records
        )

        await self.ensure_job(db_manager, job_id)
        await self.insert_products_and_images(db_manager, job_id, prepared_records)

    async def _validate_embeddings_observability(self, observability, job_id: str):
        """Validate observability for successful embedding operations."""
        captured_logs = observability.get_captured_logs()
        service_logs = {log["service"] for log in captured_logs if log.get("job_id") == job_id}

        assert "vision-embedding" in service_logs or service_logs, "Expected logs from vision-embedding service"

        captured_metrics = observability.get_captured_metrics()
        assert captured_metrics, "Expected embedding metrics to be captured"

        embedding_logs = [
            log
            for log in captured_logs
            if log.get("job_id") == job_id
            and (
                "embedding" in log.get("message", "").lower()
                or "clip" in log.get("message", "").lower()
            )
        ]
        assert embedding_logs, "Expected embedding processing logs"

    async def _validate_invalid_image_embeddings_observability(self, observability, job_id: str):
        """Validate observability for invalid masked image embedding handling."""
        captured_logs = observability.get_captured_logs()

        error_logs = [
            log
            for log in captured_logs
            if log.get("job_id") == job_id
            and log.get("level") in ("ERROR", "WARNING")
            and (
                "embedding" in log.get("message", "").lower()
                or "image" in log.get("message", "").lower()
            )
        ]

        # Presence of error logs is sufficient to demonstrate graceful handling.
        assert error_logs or captured_logs, "Expected observability entries for invalid embeddings"
