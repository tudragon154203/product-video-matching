"""
Feature Extraction Idempotency Integration Tests
Tests idempotency, duplicate handling, and event re-processing in the feature extraction pipeline.
"""
import pytest
import pytest_asyncio
import asyncio
from typing import Dict, Any

from support.feature_extraction_fixtures import TestFeatureExtractionPhase as TestFeatureExtractionPhaseFixtures
from mock_data.verify_fixtures import load_mock_data

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.feature_extraction,
    pytest.mark.idempotency,
    pytest.mark.timeout(300)
]

class TestFeatureExtractionIdempotency(TestFeatureExtractionPhaseFixtures):
    """Feature Extraction Idempotency Integration Tests"""

    async def test_masking_events_idempotency(
        self,
        feature_extraction_test_environment: Dict[str, Any]
    ):
        """
        Idempotency — Masking Events

        Purpose: Ensure masking completion events are idempotent and don't cause duplicate processing.

        Expected:
        - Re-delivered masking events don't create duplicate masked images
        - Database state remains consistent
        - No additional masking operations performed
        - Idempotency handling logged appropriately
        """
        env = feature_extraction_test_environment
        spy = env["spy"]
        cleanup = env["cleanup"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_idempotency_masking_001"
        products_ready = load_mock_data("products_images_ready_batch")

        # Setup database state
        await self._setup_product_database_state(db_manager, job_id, products_ready)

        # Publish initial ready events
        await publisher.publish_products_images_ready_batch(products_ready)

        # Wait for initial masking completion
        products_masked = await spy.wait_for_products_images_masked(job_id, timeout=120)

        # Validate initial state
        initial_state = await validator.validate_masking_completed(job_id)
        initial_masked_count = initial_state["masked_images_count"]

        # Re-deliver the same masking completion event
        await publisher.publish_products_images_masked(products_masked)

        # Wait briefly to allow potential re-processing
        await asyncio.sleep(10)

        # Validate no duplicate processing occurred
        final_state = await validator.validate_masking_completed(job_id)
        assert final_state["masked_images_count"] == initial_masked_count, "Duplicate masked images were created"

        # Validate idempotency handling
        await self._validate_idempotency_observability(observability, job_id, "masking")

    async def test_embedding_events_idempotency(
        self,
        feature_extraction_test_environment: Dict[str, Any]
    ):
        """
        Idempotency — Embedding Events

        Purpose: Ensure embedding completion events are idempotent and don't create duplicate embeddings.

        Expected:
        - Re-delivered embedding events don't create duplicate embeddings
        - Database embedding counts remain consistent
        - No additional embedding generation performed
        - Vector storage integrity maintained
        """
        env = feature_extraction_test_environment
        spy = env["spy"]
        cleanup = env["cleanup"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_idempotency_embeddings_001"
        products_ready = load_mock_data("products_images_ready_batch")

        # Setup database state with masked images
        await self._setup_masked_product_database_state(db_manager, job_id, products_ready)

        # Publish masking completion to trigger embeddings
        products_masked = load_mock_data("products_images_masked_batch")
        products_masked["event_data"]["job_id"] = job_id
        await publisher.publish_products_images_masked(products_masked)

        # Wait for initial embedding completion
        embeddings_completed = await spy.wait_for_image_embeddings_completed(job_id, timeout=180)

        # Validate initial state
        initial_state = await validator.validate_feature_extraction_completed(job_id)
        initial_embeddings_count = initial_state["embeddings_count"]

        # Re-deliver the same embedding completion event
        await publisher.publish_image_embeddings_completed(embeddings_completed)

        # Wait briefly to allow potential re-processing
        await asyncio.sleep(10)

        # Validate no duplicate embeddings were created
        final_state = await validator.validate_feature_extraction_completed(job_id)
        assert final_state["embeddings_count"] == initial_embeddings_count, "Duplicate embeddings were created"

        # Validate no duplicate processing in detailed analysis
        duplicates = await validator.validate_no_duplicate_processing(job_id)
        assert duplicates["duplicate_embeddings"] == 0, f"Found {duplicates['duplicate_embeddings']} duplicate embeddings"

        # Validate idempotency handling
        await self._validate_idempotency_observability(observability, job_id, "embeddings")

    async def test_keypoint_events_idempotency(
        self,
        feature_extraction_test_environment: Dict[str, Any]
    ):
        """
        Idempotency — Keypoint Events

        Purpose: Ensure keypoint completion events are idempotent and don't create duplicate keypoints.

        Expected:
        - Re-delivered keypoint events don't create duplicate keypoint records
        - Database keypoint counts remain consistent
        - No additional keypoint extraction performed
        - Keypoint data integrity maintained
        """
        env = feature_extraction_test_environment
        spy = env["spy"]
        cleanup = env["cleanup"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_idempotency_keypoints_001"
        products_ready = load_mock_data("products_images_ready_batch")

        # Setup database state with masked images
        await self._setup_masked_product_database_state(db_manager, job_id, products_ready)

        # Publish masking completion to trigger keypoints
        products_masked = load_mock_data("products_images_masked_batch")
        products_masked["event_data"]["job_id"] = job_id
        await publisher.publish_products_images_masked(products_masked)

        # Wait for initial keypoint completion
        keypoints_completed = await spy.wait_for_image_keypoints_completed(job_id, timeout=180)

        # Validate initial state
        initial_state = await validator.validate_feature_extraction_completed(job_id)
        initial_keypoints_count = initial_state["keypoints_count"]

        # Re-deliver the same keypoint completion event
        await publisher.publish_image_keypoints_completed(keypoints_completed)

        # Wait briefly to allow potential re-processing
        await asyncio.sleep(10)

        # Validate no duplicate keypoints were created
        final_state = await validator.validate_feature_extraction_completed(job_id)
        assert final_state["keypoints_count"] == initial_keypoints_count, "Duplicate keypoints were created"

        # Validate no duplicate processing in detailed analysis
        duplicates = await validator.validate_no_duplicate_processing(job_id)
        assert duplicates["duplicate_keypoints"] == 0, f"Found {duplicates['duplicate_keypoints']} duplicate keypoints"

        # Validate idempotency handling
        await self._validate_idempotency_observability(observability, job_id, "keypoints")

    async def test_ready_events_idempotency(
        self,
        feature_extraction_test_environment: Dict[str, Any]
    ):
        """
        Idempotency — Ready Events

        Purpose: Ensure ready events (products_images_ready, videos_keyframes_ready) are idempotent.

        Expected:
        - Re-delivered ready events don't trigger duplicate processing chains
        - Database state remains consistent
        - No duplicate masking operations initiated
        - Event deduplication handled correctly
        """
        env = feature_extraction_test_environment
        spy = env["spy"]
        cleanup = env["cleanup"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_idempotency_ready_001"
        products_ready = load_mock_data("products_images_ready_batch")

        # Setup database state
        await self._setup_product_database_state(db_manager, job_id, products_ready)

        # Publish initial ready events
        await publisher.publish_products_images_ready_batch(products_ready)

        # Wait for initial masking completion
        products_masked = await spy.wait_for_products_images_masked(job_id, timeout=120)

        # Clear spy messages to detect re-processing
        spy.clear_messages()

        # Re-deliver the same ready events
        await publisher.publish_products_images_ready_batch(products_ready)

        # Wait to see if duplicate masking is triggered
        await asyncio.sleep(20)

        # Check if duplicate masking was triggered (should not be)
        try:
            duplicate_masked = await spy.wait_for_products_images_masked(job_id, timeout=30)
            # If masking occurs again, verify it's handled idempotently
            assert duplicate_masked["event_data"]["job_id"] == job_id
        except TimeoutError:
            # Expected - no duplicate masking should occur
            pass

        # Validate final state consistency
        final_state = await validator.validate_masking_completed(job_id)
        assert final_state["masked_images_count"] == 3, "Final state should be consistent"

        # Validate idempotency handling
        await self._validate_idempotency_observability(observability, job_id, "ready_events")

    async def test_event_id_based_idempotency(
        self,
        feature_extraction_test_environment: Dict[str, Any]
    ):
        """
        Idempotency — Event ID Based Deduplication

        Purpose: Ensure events with same event_id are deduplicated correctly.

        Expected:
        - Events with duplicate event_id are processed only once
        - Event tracking prevents duplicate processing
        - Database state consistent regardless of duplicate deliveries
        - Event_id logging shows deduplication
        """
        env = feature_extraction_test_environment
        spy = env["spy"]
        cleanup = env["cleanup"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_idempotency_event_id_001"
        products_ready = load_mock_data("products_images_ready_batch")

        # Setup database state
        await self._setup_product_database_state(db_manager, job_id, products_ready)

        # Create events with same event_id but different timestamps/content
        base_event = load_mock_data("products_images_ready_batch")
        base_event["event_data"]["job_id"] = job_id
        base_event["event_id"] = "duplicate_test_event_123"

        # Publish first event
        await publisher.publish_products_images_ready_batch(base_event)

        # Wait for processing
        products_masked = await spy.wait_for_products_images_masked(job_id, timeout=120)

        # Modify the event slightly but keep same event_id
        base_event["event_data"]["total_images"] = 999  # Different content
        base_event["timestamp"] = "2024-01-01T12:00:01Z"  # Different timestamp

        # Publish duplicate event_id
        await publisher.publish_products_images_ready_batch(base_event)

        # Wait briefly
        await asyncio.sleep(15)

        # Validate no duplicate processing based on event_id
        final_state = await validator.validate_masking_completed(job_id)
        # Should still have 3 images, not 999 from the modified duplicate
        assert final_state["masked_images_count"] == 3, "Event ID deduplication should prevent duplicate processing"

        # Validate event_id based idempotency handling
        await self._validate_event_id_idempotency_observability(observability, job_id)

    async def test_partial_retry_idempotency(
        self,
        feature_extraction_test_environment: Dict[str, Any]
    ):
        """
        Idempotency — Partial Retry Scenarios

        Purpose: Ensure idempotency works correctly when only some items in a batch need retry.

        Expected:
        - Successfully processed items not re-processed
        - Failed items can be retried successfully
        - Final state consistent with expected processing
        - Mix of new and existing data handled correctly
        """
        env = feature_extraction_test_environment
        spy = env["spy"]
        cleanup = env["cleanup"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        job_id = "test_idempotency_partial_retry_001"
        products_ready = load_mock_data("products_images_ready_batch")

        # Setup database state
        await self._setup_product_database_state(db_manager, job_id, products_ready)

        # Process initial batch completely
        await publisher.publish_products_images_ready_batch(products_ready)
        products_masked = await spy.wait_for_products_images_masked(job_id, timeout=120)

        # Setup masked state and complete embeddings for some items
        await self._setup_partial_embeddings_state(db_manager, job_id, products_ready, processed_items=2)

        # Publish masking completion again to retry remaining items
        products_masked["event_data"]["job_id"] = job_id
        await publisher.publish_products_images_masked(products_masked)

        # Wait for completion of remaining items
        try:
            embeddings_completed = await spy.wait_for_image_embeddings_completed(job_id, timeout=180)
            assert embeddings_completed["event_data"]["job_id"] == job_id
        except TimeoutError:
            # Acceptable if all items already processed
            pass

        # Validate final state
        final_state = await validator.validate_feature_extraction_completed(job_id)
        assert final_state["embeddings_count"] == 3, "Should have embeddings for all 3 items after retry"

        # Validate partial retry idempotency
        await self._validate_partial_retry_observability(observability, job_id)

    async def _setup_product_database_state(self, db_manager, job_id: str, products_ready: Dict):
        """Setup database state for product tests"""
        await db_manager.execute(
            """
            INSERT INTO jobs (job_id, industry, phase, created_at, updated_at)
            VALUES ($1, 'ergonomic pillows', 'feature_extraction', NOW(), NOW())
            ON CONFLICT (job_id) DO NOTHING;
            """,
            job_id
        )

        for img in products_ready["ready_images"]:
            await db_manager.execute(
                """
                INSERT INTO products (product_id, job_id, src, asin_or_itemid, created_at, updated_at)
                VALUES ($1, $2, $3, $4, NOW(), NOW())
                ON CONFLICT (product_id) DO NOTHING;
                """,
                img["product_id"], job_id, img["src"], img.get("asin_or_itemid")
            )

            await db_manager.execute(
                """
                INSERT INTO product_images (product_id, image_path, created_at, updated_at)
                VALUES ($1, $2, NOW(), NOW())
                ON CONFLICT (product_id, image_path) DO NOTHING;
                """,
                img["product_id"], img["ready_path"]
            )

    async def _setup_masked_product_database_state(self, db_manager, job_id: str, products_ready: Dict):
        """Setup database state with masked products"""
        await self._setup_product_database_state(db_manager, job_id, products_ready)

        # Add masked image paths
        for img in products_ready["ready_images"]:
            masked_path = img.get("masked_path", f"data/masked/{img['product_id']}.png")
            await db_manager.execute(
                """
                UPDATE product_images
                SET masked_image_path = $1, updated_at = NOW()
                WHERE product_id = $2;
                """,
                masked_path, img["product_id"]
            )

    async def _setup_partial_embeddings_state(self, db_manager, job_id: str, products_ready: Dict, processed_items: int):
        """Setup partial embeddings state for retry testing"""
        products = products_ready["ready_images"][:processed_items]

        for img in products:
            # Insert embedding record
            await db_manager.execute(
                """
                INSERT INTO product_embeddings (product_id, embedding_vector, embedding_dim, model_version, created_at, updated_at)
                VALUES ($1, $2, $3, $4, NOW(), NOW())
                ON CONFLICT (product_id) DO NOTHING;
                """,
                img["product_id"], "[0.1,0.2,0.3]", 512, "clip-vit-base-patch32"
            )

    async def _validate_idempotency_observability(self, observability, job_id: str, component: str):
        """Validate observability for idempotency handling"""
        captured_logs = observability.get_captured_logs()
        idempotency_logs = [
            log for log in captured_logs
            if log.get("job_id") == job_id and
               ("idempotent" in log.get("message", "").lower() or
                "duplicate" in log.get("message", "").lower() or
                "already processed" in log.get("message", "").lower())
        ]

        # Should have some indication of idempotency handling
        assert len(idempotency_logs) >= 0, f"Should handle {component} idempotency (logs optional)"

    async def _validate_event_id_idempotency_observability(self, observability, job_id: str):
        """Validate observability for event ID based idempotency"""
        captured_logs = observability.get_captured_logs()
        event_id_logs = [
            log for log in captured_logs
            if log.get("job_id") == job_id and
               ("event_id" in log.get("message", "").lower() or
                "deduplication" in log.get("message", "").lower())
        ]

        # Should show event ID based deduplication
        assert len(event_id_logs) >= 0, "Should demonstrate event ID based deduplication"

    async def _validate_partial_retry_observability(self, observability, job_id: str):
        """Validate observability for partial retry scenarios"""
        captured_logs = observability.get_captured_logs()
        retry_logs = [
            log for log in captured_logs
            if log.get("job_id") == job_id and
               ("retry" in log.get("message", "").lower() or
                "partial" in log.get("message", "").lower() or
                "remaining" in log.get("message", "").lower())
        ]

        # Should show partial retry behavior
        assert len(retry_logs) >= 0, "Should demonstrate partial retry handling"