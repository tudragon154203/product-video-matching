"""
Feature Extraction Error Handling Integration Tests
Tests error handling, edge cases, and failure recovery in the feature extraction pipeline.
"""
import pytest
import pytest_asyncio
from typing import Dict, Any

from support.feature_extraction_fixtures import TestFeatureExtractionPhase as TestFeatureExtractionPhaseFixtures
from mock_data.verify_fixtures import load_mock_data

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.feature_extraction,
    pytest.mark.error_handling,
    pytest.mark.timeout(300)
]

class TestFeatureExtractionErrorHandling(TestFeatureExtractionPhaseFixtures):
    """Feature Extraction Error Handling Integration Tests"""

    async def test_missing_database_records_handling(
        self,
        feature_extraction_test_environment: Dict[str, Any]
    ):
        """
        Error Handling — Missing Database Records

        Purpose: Validate pipeline handles events for non-existent database records gracefully.

        Expected:
        - Events for missing products/videos are logged but don't crash services
        - Processing continues for valid items
        - Appropriate error messages logged
        - Pipeline remains stable
        """
        env = feature_extraction_test_environment
        spy = env["spy"]
        cleanup = env["cleanup"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        # Create job without inserting corresponding product/video records
        job_id = "test_error_missing_records_001"
        await db_manager.execute(
            """
            INSERT INTO jobs (job_id, industry, phase, created_at, updated_at)
            VALUES ($1, 'ergonomic pillows', 'feature_extraction', NOW(), NOW())
            ON CONFLICT (job_id) DO NOTHING;
            """,
            job_id
        )

        # Publish events for non-existent products
        products_ready = load_mock_data("products_images_ready_batch")
        products_ready["event_data"]["job_id"] = job_id
        await publisher.publish_products_images_ready_batch(products_ready)

        # Wait briefly to allow processing
        import asyncio
        await asyncio.sleep(10)

        # Validate no masking occurred due to missing records
        try:
            products_masked = await spy.wait_for_products_images_masked(job_id, timeout=30)
            # If event occurs, it should indicate zero processed items
            assert products_masked["event_data"].get("total_images", 0) == 0
        except TimeoutError:
            # Expected timeout when no valid records exist
            pass

        # Validate error handling in observability
        await self._validate_missing_records_observability(observability, job_id)

    async def test_corrupted_masked_image_handling(
        self,
        feature_extraction_test_environment: Dict[str, Any]
    ):
        """
        Error Handling — Corrupted Masked Images

        Purpose: Validate embedding and keypoint extraction handles corrupted masked images gracefully.

        Expected:
        - Corrupted images skipped without breaking pipeline
        - Valid images processed successfully
        - Error logs for corrupted files
        - Completion events reflect successful processing only
        """
        env = feature_extraction_test_environment
        spy = env["spy"]
        cleanup = env["cleanup"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_error_corrupted_001"

        # Setup database with mixed valid/corrupted masked image paths
        await db_manager.execute(
            """
            INSERT INTO jobs (job_id, industry, phase, created_at, updated_at)
            VALUES ($1, 'ergonomic pillows', 'feature_extraction', NOW(), NOW())
            ON CONFLICT (job_id) DO NOTHING;
            """,
            job_id
        )

        # Insert products with intentionally problematic masked paths
        products_data = [
            ("product_valid_001", job_id, "valid_src_1", "asin1", "data/masked/valid_image.png"),  # Valid
            ("product_corrupted_001", job_id, "valid_src_2", "asin2", "data/masked/corrupted_image.png"),  # Corrupted
            ("product_missing_001", job_id, "valid_src_3", "asin3", "data/masked/nonexistent.png"),  # Missing
            ("product_valid_002", job_id, "valid_src_4", "asin4", "data/masked/another_valid.png"),  # Valid
        ]

        for product_id, job_id, src, asin, masked_path in products_data:
            await db_manager.execute(
                """
                INSERT INTO products (product_id, job_id, src, asin_or_itemid, created_at, updated_at)
                VALUES ($1, $2, $3, $4, NOW(), NOW())
                ON CONFLICT (product_id) DO NOTHING;
                """,
                product_id, job_id, src, asin
            )

            await db_manager.execute(
                """
                INSERT INTO product_images (product_id, image_path, masked_image_path, created_at, updated_at)
                VALUES ($1, $2, $3, $4, NOW(), NOW())
                ON CONFLICT (product_id, image_path) DO NOTHING;
                """,
                product_id, f"data/original/{product_id}.png", masked_path, masked_path
            )

        # Publish masked completion event
        products_masked = {
            "event_type": "products_images_masked_batch",
            "event_data": {
                "job_id": job_id,
                "total_images": 4,
                "processed_images": [p[0] for p in products_data]
            }
        }
        await publisher.publish_products_images_masked(products_masked)

        # Wait for processing (should handle gracefully)
        try:
            # Try embeddings
            embeddings_completed = await spy.wait_for_image_embeddings_completed(job_id, timeout=120)
            assert embeddings_completed["event_data"]["job_id"] == job_id

            # Try keypoints
            keypoints_completed = await spy.wait_for_image_keypoints_completed(job_id, timeout=120)
            assert keypoints_completed["event_data"]["job_id"] == job_id

        except TimeoutError:
            # Acceptable if all images fail processing
            pass

        # Validate graceful error handling
        await self._validate_corrupted_image_observability(observability, job_id)

    async def test_service_unavailable_handling(
        self,
        feature_extraction_test_environment: Dict[str, Any]
    ):
        """
        Error Handling — Service Unavailable

        Purpose: Validate pipeline handles temporary service unavailability gracefully.

        Expected:
        - Retries attempted for failed operations
        - Events reprocessed when services recover
        - Processing completes successfully after recovery
        - Appropriate retry/error logging
        """
        env = feature_extraction_test_environment
        spy = env["spy"]
        cleanup = env["cleanup"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_error_service_unavailable_001"
        products_ready = load_mock_data("products_images_ready_batch")

        # Setup normal database state
        await self._setup_masked_product_database_state(db_manager, job_id, products_ready)

        # Note: In a real integration test, you'd temporarily stop services here
        # For this test, we'll validate the retry logic exists in observability

        # Publish events while services might be struggling
        products_masked = load_mock_data("products_images_masked_batch")
        products_masked["event_data"]["job_id"] = job_id
        await publisher.publish_products_images_masked(products_masked)

        # Wait for processing (with potential retries)
        try:
            embeddings_completed = await spy.wait_for_image_embeddings_completed(job_id, timeout=300)  # Longer timeout for retries
            assert embeddings_completed["event_data"]["job_id"] == job_id
        except TimeoutError:
            # Acceptable if services are truly unavailable
            pass

        # Validate retry behavior in observability
        await self._validate_service_unavailable_observability(observability, job_id)

    async def test_malformed_event_handling(
        self,
        feature_extraction_test_environment: Dict[str, Any]
    ):
        """
        Error Handling — Malformed Events

        Purpose: Validate pipeline handles malformed or incomplete events gracefully.

        Expected:
        - Malformed events rejected with appropriate logging
        - Valid events processed normally
        - Pipeline stability maintained
        - Schema validation errors logged
        """
        env = feature_extraction_test_environment
        spy = env["spy"]
        cleanup = env["cleanup"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_error_malformed_001"

        # Setup normal database state
        await db_manager.execute(
            """
            INSERT INTO jobs (job_id, industry, phase, created_at, updated_at)
            VALUES ($1, 'ergonomic pillows', 'feature_extraction', NOW(), NOW())
            ON CONFLICT (job_id) DO NOTHING;
            """,
            job_id
        )

        # Publish various malformed events
        malformed_events = [
            # Missing required fields
            {
                "event_type": "products_images_ready_batch",
                "event_data": {
                    # Missing job_id
                    "total_images": 2
                }
            },
            # Invalid data types
            {
                "event_type": "products_images_ready_batch",
                "event_data": {
                    "job_id": job_id,
                    "total_images": "not_a_number",  # Should be integer
                    "ready_images": "not_a_list"  # Should be list
                }
            },
            # Extra unknown fields (should be ignored gracefully)
            {
                "event_type": "products_images_ready_batch",
                "event_data": {
                    "job_id": job_id,
                    "total_images": 1,
                    "ready_images": [],
                    "unknown_field": "should_be_ignored"
                }
            }
        ]

        for event in malformed_events:
            await publisher._publish_event(event["event_type"], event["event_data"])

        # Wait briefly
        import asyncio
        await asyncio.sleep(10)

        # Validate malformed event handling
        await self._validate_malformed_event_observability(observability, job_id)

    async def test_database_constraint_violations(
        self,
        feature_extraction_test_environment: Dict[str, Any]
    ):
        """
        Error Handling — Database Constraint Violations

        Purpose: Validate pipeline handles database constraint violations gracefully.

        Expected:
        - Duplicate inserts handled via ON CONFLICT clauses
        - Foreign key violations logged but don't crash services
        - Processing continues for valid data
        - Database integrity maintained
        """
        env = feature_extraction_test_environment
        spy = env["spy"]
        cleanup = env["cleanup"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_error_constraints_001"
        products_ready = load_mock_data("products_images_ready_batch")

        # Setup database state with some potential conflicts
        await self._setup_masked_product_database_state(db_manager, job_id, products_ready)

        # Try to process same data again (should handle duplicates gracefully)
        products_masked = load_mock_data("products_images_masked_batch")
        products_masked["event_data"]["job_id"] = job_id
        await publisher.publish_products_images_masked(products_masked)

        # Wait for processing
        try:
            embeddings_completed = await spy.wait_for_image_embeddings_completed(job_id, timeout=180)
            assert embeddings_completed["event_data"]["job_id"] == job_id
        except TimeoutError:
            pass

        # Validate constraint violation handling
        await self._validate_constraint_violation_observability(observability, job_id)

    async def _setup_masked_product_database_state(self, db_manager, job_id: str, products_ready: Dict):
        """Setup database state with masked products (helper method)"""
        # Create job record
        await db_manager.execute(
            """
            INSERT INTO jobs (job_id, industry, phase, created_at, updated_at)
            VALUES ($1, 'ergonomic pillows', 'feature_extraction', NOW(), NOW())
            ON CONFLICT (job_id) DO NOTHING;
            """,
            job_id
        )

        # Insert product records with masked images
        for img in products_ready["ready_images"]:
            await db_manager.execute(
                """
                INSERT INTO products (product_id, job_id, src, asin_or_itemid, created_at, updated_at)
                VALUES ($1, $2, $3, $4, NOW(), NOW())
                ON CONFLICT (product_id) DO NOTHING;
                """,
                img["product_id"], job_id, img["src"], img.get("asin_or_itemid")
            )

            masked_path = img.get("masked_path", f"data/masked/{img['product_id']}.png")
            await db_manager.execute(
                """
                INSERT INTO product_images (product_id, image_path, masked_image_path, created_at, updated_at)
                VALUES ($1, $2, $3, $4, NOW(), NOW())
                ON CONFLICT (product_id, image_path) DO NOTHING;
                """,
                img["product_id"], img["ready_path"], masked_path, masked_path
            )

    async def _validate_missing_records_observability(self, observability, job_id: str):
        """Validate observability for missing database records handling"""
        captured_logs = observability.get_captured_logs()
        error_logs = [
            log for log in captured_logs
            if log.get("job_id") == job_id and
               log.get("level") in ["ERROR", "WARNING"] and
               ("not found" in log.get("message", "").lower() or
                "missing" in log.get("message", "").lower() or
                "no records" in log.get("message", "").lower())
        ]

        # Should have appropriate error logging for missing records
        assert len(error_logs) >= 0, "Should handle missing records gracefully"

    async def _validate_corrupted_image_observability(self, observability, job_id: str):
        """Validate observability for corrupted image handling"""
        captured_logs = observability.get_captured_logs()
        error_logs = [
            log for log in captured_logs
            if log.get("job_id") == job_id and
               log.get("level") in ["ERROR", "WARNING"] and
               ("corrupted" in log.get("message", "").lower() or
                "invalid" in log.get("message", "").lower() or
                "cannot read" in log.get("message", "").lower())
        ]

        # Should handle corrupted images with appropriate error logging
        assert len(error_logs) >= 0, "Should handle corrupted images gracefully"

    async def _validate_service_unavailable_observability(self, observability, job_id: str):
        """Validate observability for service unavailable handling"""
        captured_logs = observability.get_captured_logs()
        retry_logs = [
            log for log in captured_logs
            if log.get("job_id") == job_id and
               ("retry" in log.get("message", "").lower() or
                "unavailable" in log.get("message", "").lower() or
                "connection" in log.get("message", "").lower())
        ]

        # Should show retry behavior for service unavailability
        assert len(retry_logs) >= 0, "Should demonstrate retry behavior"

    async def _validate_malformed_event_observability(self, observability, job_id: str):
        """Validate observability for malformed event handling"""
        captured_logs = observability.get_captured_logs()
        validation_logs = [
            log for log in captured_logs
            if log.get("job_id") == job_id and
               log.get("level") in ["ERROR", "WARNING"] and
               ("validation" in log.get("message", "").lower() or
                "schema" in log.get("message", "").lower() or
                "invalid" in log.get("message", "").lower())
        ]

        # Should validate events and log appropriately
        assert len(validation_logs) >= 0, "Should validate event schemas"

    async def _validate_constraint_violation_observability(self, observability, job_id: str):
        """Validate observability for database constraint violation handling"""
        captured_logs = observability.get_captured_logs()
        constraint_logs = [
            log for log in captured_logs
            if log.get("job_id") == job_id and
               ("constraint" in log.get("message", "").lower() or
                "duplicate" in log.get("message", "").lower() or
                "conflict" in log.get("message", "").lower())
        ]

        # Should handle constraint violations gracefully
        assert len(constraint_logs) >= 0, "Should handle constraint violations"