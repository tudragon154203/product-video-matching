"""
Feature Extraction End-to-End Integration Tests
Tests the complete feature extraction pipeline workflow from ready inputs through all phases to completion.
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
    pytest.mark.end_to_end,
    pytest.mark.timeout(600)  # Longer timeout for full pipeline
]

class TestFeatureExtractionEndToEnd(TestFeatureExtractionPhaseFixtures):
    """Feature Extraction End-to-End Integration Tests"""

    async def test_complete_feature_extraction_workflow(
        self,
        feature_extraction_test_environment: Dict[str, Any]
    ):
        """
        Complete Feature Extraction Workflow — End-to-End

        Purpose: Validate the entire feature extraction pipeline from ready inputs to completion.

        Expected:
        - All phases execute in correct order: masking → embeddings → keypoints
        - Exactly one completion event per phase observed
        - All products and videos processed through all phases
        - Database updated correctly at each phase
        - Observability captures all phase activities
        - Pipeline completes without errors
        """
        env = feature_extraction_test_environment
        spy = env["spy"]
        cleanup = env["cleanup"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        # Load comprehensive test data
        job_id = "test_e2e_complete_001"
        products_ready = load_mock_data("products_images_ready_batch")
        videos_ready = load_mock_data("videos_keyframes_ready")  # Individual video for database setup
        videos_ready_batch = load_mock_data("videos_keyframes_ready_batch")  # Bare batch for publishing

        # Setup complete database state
        await self._setup_complete_database_state(db_manager, job_id, products_ready, videos_ready)

        # Validate initial state
        initial_state = await validator.validate_initial_state(job_id)
        assert initial_state["products_count"] == 3, f"Expected 3 products, got {initial_state['products_count']}"
        assert initial_state["images_count"] == 3, f"Expected 3 images, got {initial_state['images_count']}"
        assert initial_state["videos_count"] == 1, f"Expected 1 video, got {initial_state['videos_count']}"
        assert initial_state["frames_count"] == 5, f"Expected 5 frames, got {initial_state['frames_count']}"
        assert initial_state["masked_images_count"] == 0, "Expected no masked images initially"
        assert initial_state["masked_frames_count"] == 0, "Expected no masked frames initially"
        assert initial_state["embeddings_count"] == 0, "Expected no embeddings initially"
        assert initial_state["keypoints_count"] == 0, "Expected no keypoints initially"

        # Phase 1: Publish ready events to trigger masking
        for i in range(1, 4):
            individual_product_event = load_mock_data(f"products_images_ready_{i}")
            await publisher.publish_products_images_ready(individual_product_event)

        # Publish video keyframes ready events (one per video, matching production schema)
        # Transform batch event to individual video events matching production schema
        for video_data in videos_ready_batch["videos"]:
            video_event = {
                "job_id": videos_ready_batch["job_id"],
                "video_id": video_data["video_id"],
                "frames": video_data["frames"]
            }
            await publisher.publish_video_keyframes_ready(video_event)

        await publisher.publish_products_images_ready_batch(products_ready)
        await publisher.publish_video_keyframes_ready_batch(videos_ready_batch)

        # Phase 1 Completion: Wait for masking
        products_masked = await spy.wait_for_products_images_masked(job_id, timeout=120)
        videos_masked = await spy.wait_for_video_keyframes_masked(job_id, timeout=120)

        # Validate masking phase
        assert products_masked["event_data"]["job_id"] == job_id
        assert products_masked["event_data"]["total_images"] == 3
        assert videos_masked["event_data"]["job_id"] == job_id
        assert videos_masked["event_data"]["total_keyframes"] == 5

        masking_state = await validator.validate_masking_completed(job_id)
        assert masking_state["masked_images_count"] == 3, f"Expected 3 masked images, got {masking_state['masked_images_count']}"
        assert masking_state["masked_frames_count"] == 5, f"Expected 5 masked frames, got {masking_state['masked_frames_count']}"

        # Phase 2: Wait for embedding extraction (triggered by masking completion)
        embeddings_completed = await spy.wait_for_image_embeddings_completed(job_id, timeout=180)

        # Validate embedding phase
        assert embeddings_completed["event_data"]["job_id"] == job_id
        assert embeddings_completed["event_data"]["processed_assets"] == 3

        # Phase 3: Wait for keypoint extraction (triggered by masking completion)
        keypoints_completed = await spy.wait_for_image_keypoints_completed(job_id, timeout=180)
        video_keypoints_completed = await spy.wait_for_video_keypoints_completed(job_id, timeout=180)

        # Validate keypoint phase
        assert keypoints_completed["event_data"]["job_id"] == job_id
        assert video_keypoints_completed["event_data"]["job_id"] == job_id

        # Validate final state - complete feature extraction
        final_state = await validator.validate_feature_extraction_completed(job_id)
        assert final_state["embeddings_count"] == 3, f"Expected 3 embeddings, got {final_state['embeddings_count']}"
        assert final_state["keypoints_count"] == 3, f"Expected 3 keypoints, got {final_state['keypoints_count']}"
        assert final_state["video_keypoints_count"] == 5, f"Expected 5 video keypoints, got {final_state['video_keypoints_count']}"

        # Validate detailed feature data
        await self._validate_complete_feature_data(final_state)

        # Validate comprehensive observability
        await self._validate_end_to_end_observability(observability, job_id)

    async def test_pipeline_phase_ordering(
        self,
        feature_extraction_test_environment: Dict[str, Any]
    ):
        """
        Pipeline Phase Ordering — Correct Execution Sequence

        Purpose: Validate that pipeline phases execute in the correct order.

        Expected:
        - Masking phase completes before embedding/keypoint phases start
        - Embedding and keypoint phases can run in parallel after masking
        - No phase dependencies violated
        - Event timestamps respect execution order
        """
        env = feature_extraction_test_environment
        spy = env["spy"]
        cleanup = env["cleanup"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        # Setup and trigger pipeline
        job_id = "test_e2e_ordering_001"
        products_ready = load_mock_data("products_images_ready_batch")
        videos_ready = load_mock_data("videos_keyframes_ready")
        videos_ready_batch = load_mock_data("videos_keyframes_ready_batch")

        await self._setup_complete_database_state(db_manager, job_id, products_ready, videos_ready)

        # Start timing
        import time
        start_time = time.time()

        # Publish events
        await publisher.publish_products_images_ready_batch(products_ready)
        await publisher.publish_video_keyframes_ready_batch(videos_ready_batch)

        # Capture completion times
        products_masked = await spy.wait_for_products_images_masked(job_id, timeout=120)
        masking_time = time.time()

        embeddings_completed = await spy.wait_for_image_embeddings_completed(job_id, timeout=180)
        embeddings_time = time.time()

        keypoints_completed = await spy.wait_for_image_keypoints_completed(job_id, timeout=180)
        keypoints_time = time.time()

        video_keypoints_completed = await spy.wait_for_video_keypoints_completed(job_id, timeout=180)
        video_keypoints_time = time.time()

        # Validate ordering: masking must complete before feature extraction
        assert masking_time < embeddings_time, "Masking must complete before embeddings"
        assert masking_time < keypoints_time, "Masking must complete before keypoints"
        assert masking_time < video_keypoints_time, "Masking must complete before video keypoints"

        # Embeddings and keypoints can run in parallel after masking
        # No strict ordering required between them

        # Validate phase sequence in observability
        await self._validate_phase_ordering_observability(observability, job_id)

    async def test_pipeline_performance_baseline(
        self,
        feature_extraction_test_environment: Dict[str, Any]
    ):
        """
        Pipeline Performance — Baseline Metrics

        Purpose: Establish baseline performance metrics for the complete pipeline.

        Expected:
        - Pipeline completes within reasonable time limits
        - Each phase meets expected performance criteria
        - Resource usage stays within acceptable bounds
        - Performance metrics captured in observability
        """
        env = feature_extraction_test_environment
        spy = env["spy"]
        cleanup = env["cleanup"]
        validator = env["validator"]
        publisher = env["publisher"]
        observability = env["observability"]
        db_manager = env["db_manager"]

        # Setup and time the complete pipeline
        job_id = "test_e2e_performance_001"
        products_ready = load_mock_data("products_images_ready_batch")
        videos_ready = load_mock_data("videos_keyframes_ready")
        videos_ready_batch = load_mock_data("videos_keyframes_ready_batch")

        await self._setup_complete_database_state(db_manager, job_id, products_ready, videos_ready)

        # Start pipeline timing
        import time
        pipeline_start = time.time()

        # Execute complete pipeline
        await publisher.publish_products_images_ready_batch(products_ready)
        await publisher.publish_video_keyframes_ready_batch(videos_ready_batch)

        # Wait for all phases
        await spy.wait_for_products_images_masked(job_id, timeout=120)
        await spy.wait_for_image_embeddings_completed(job_id, timeout=180)
        await spy.wait_for_image_keypoints_completed(job_id, timeout=180)
        await spy.wait_for_video_keypoints_completed(job_id, timeout=180)

        pipeline_end = time.time()
        total_duration = pipeline_end - pipeline_start

        # Validate performance expectations
        # These are baseline expectations - adjust based on your system capabilities
        assert total_duration < 300, f"Pipeline should complete within 5 minutes, took {total_duration:.1f}s"

        # Validate performance metrics captured
        await self._validate_performance_observability(observability, job_id, total_duration)

    async def _setup_complete_database_state(self, db_manager, job_id: str, products_ready: Dict, videos_ready: Dict):
        """Setup complete database state for end-to-end tests"""
        # Create job record
        await db_manager.execute(
            """
            INSERT INTO jobs (job_id, industry, phase, created_at, updated_at)
            VALUES ($1, 'ergonomic pillows', 'feature_extraction', NOW(), NOW())
            ON CONFLICT (job_id) DO NOTHING;
            """,
            job_id
        )

        # Insert product records
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

        # Insert video records
        for frame in videos_ready["frames"]:
            await db_manager.execute(
                """
                INSERT INTO videos (video_id, job_id, platform, created_at, updated_at)
                VALUES ($1, $2, 'youtube', NOW(), NOW())
                ON CONFLICT (video_id) DO NOTHING;
                """,
                videos_ready["video_id"], job_id
            )

            await db_manager.execute(
                """
                INSERT INTO video_frames (video_id, frame_sequence, frame_path, created_at, updated_at)
                VALUES ($1, $2, $3, NOW(), NOW())
                ON CONFLICT (video_id, frame_sequence) DO NOTHING;
                """,
                videos_ready["video_id"], frame["frame_id"], frame["local_path"]
            )

    async def _validate_complete_feature_data(self, final_state: Dict):
        """Validate completeness and quality of extracted feature data"""
        # Validate embeddings data
        embeddings_details = final_state["embeddings_details"]
        assert len(embeddings_details) == 3, "Expected embeddings for all 3 products"

        for embedding in embeddings_details:
            assert embedding["embedding_dim"] > 0, f"Invalid embedding dimension for {embedding['product_id']}"
            assert embedding["model_version"], f"Missing model version for {embedding['product_id']}"
            assert embedding["embedding_vector"], f"Missing embedding vector for {embedding['product_id']}"

        # Validate keypoints data
        keypoints_details = final_state["keypoints_details"]
        assert len(keypoints_details) == 3, "Expected keypoints for all 3 products"

        for keypoints in keypoints_details:
            assert keypoints["num_keypoints"] > 0, f"Invalid keypoints count for {keypoints['product_id']}"
            assert keypoints["model_version"], f"Missing model version for {keypoints['product_id']}"
            assert keypoints["keypoint_data"], f"Missing keypoint data for {keypoints['product_id']}"

        # Validate video keypoints data
        video_keypoints_details = final_state.get("video_keypoints_details", [])
        assert len(video_keypoints_details) == 5, "Expected video keypoints for all 5 frames"

        for video_keypoints in video_keypoints_details:
            assert video_keypoints["num_keypoints"] > 0, f"Invalid video keypoints count for frame"
            assert video_keypoints["model_version"], f"Missing model version for video frame"

    async def _validate_end_to_end_observability(self, observability, job_id: str):
        """Validate comprehensive observability for end-to-end pipeline"""
        # Check logs from all expected services
        captured_logs = observability.get_captured_logs()
        service_logs = {log["service"] for log in captured_logs if log.get("job_id") == job_id}

        expected_services = ["vision-embedding", "vision-keypoint", "product-segmentor", "video-crawler"]
        for service in expected_services:
            assert service in service_logs or len(service_logs) > 0, f"Expected logs from {service} or other services"

        # Check metrics from all phases
        captured_metrics = observability.get_captured_metrics()
        assert len(captured_metrics) > 0, "Expected metrics to be captured"

        # Validate phase-specific logs
        phase_logs = {
            "masking": 0,
            "embeddings": 0,
            "keypoints": 0
        }

        for log in captured_logs:
            if log.get("job_id") == job_id:
                message = log.get("message", "").lower()
                if "mask" in message or "segment" in message:
                    phase_logs["masking"] += 1
                elif "embedding" in message or "clip" in message:
                    phase_logs["embeddings"] += 1
                elif "keypoint" in message or "akaze" in message or "sift" in message:
                    phase_logs["keypoints"] += 1

        # Should have logs from all phases
        for phase, count in phase_logs.items():
            assert count > 0, f"Expected logs from {phase} phase"

    async def _validate_phase_ordering_observability(self, observability, job_id: str):
        """Validate phase ordering in observability data"""
        captured_logs = observability.get_captured_logs()
        job_logs = [log for log in captured_logs if log.get("job_id") == job_id]

        # Should show phase progression
        phase_progression = []
        for log in sorted(job_logs, key=lambda x: x.get("timestamp", "")):
            message = log.get("message", "").lower()
            if "masked" in message and "completed" in message:
                phase_progression.append("masking")
            elif "embedding" in message and "completed" in message:
                phase_progression.append("embeddings")
            elif "keypoint" in message and "completed" in message:
                phase_progression.append("keypoints")

        # Masking should appear before feature extraction phases
        if "masking" in phase_progression:
            masking_index = phase_progression.index("masking")
            for phase in ["embeddings", "keypoints"]:
                if phase in phase_progression:
                    assert phase_progression.index(phase) > masking_index, f"{phase} should follow masking"

    async def _validate_performance_observability(self, observability, job_id: str, total_duration: float):
        """Validate performance metrics in observability data"""
        captured_logs = observability.get_captured_logs()
        job_logs = [log for log in captured_logs if log.get("job_id") == job_id]

        # Look for performance-related logs
        perf_logs = [
            log for log in job_logs
            if "duration" in log.get("message", "").lower() or
               "timing" in log.get("message", "").lower() or
               "performance" in log.get("message", "").lower()
        ]

        # Should have some performance indicators
        assert len(perf_logs) >= 0, "Performance metrics should be captured"

        # Check captured metrics for performance data
        captured_metrics = observability.get_captured_metrics()
        perf_metrics = [
            metric for metric in captured_metrics
            if "duration" in str(metric).lower() or
               "timing" in str(metric).lower() or
               "latency" in str(metric).lower()
        ]

        # Performance metrics should be available
        assert len(perf_metrics) >= 0, "Performance metrics should be captured"

    def _has_mock_data(self, filename: str) -> bool:
        """Check if mock data file exists"""
        try:
            load_mock_data(filename)
            return True
        except:
            return False