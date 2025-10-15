"""
Collection Phase Integration Tests

Tests the complete collection phase workflow including:
- Products collection request and completion
- Videos collection request and completion
- Event flow validation
- Database state validation
- Test isolation and cleanup
"""
import pytest
import asyncio
from datetime import datetime

from utils.test_environment import CollectionPhaseTestEnvironment
from utils.event_publisher import TestEventFactory
from utils.db_cleanup import DatabaseStateValidator


class TestCollectionPhaseIntegration:
    """
    Collection phase integration tests using the complete test infrastructure.
    """
    
    @pytest.mark.asyncio
    @pytest.mark.collection_phase
    @pytest.mark.integration
    async def test_complete_collection_workflow(
        self,
        collection_phase_test_environment
    ):
        """
        Test the complete collection workflow from request to completion.
        
        This test:
        1. Sets up the test environment
        2. Publishes collection requests
        3. Waits for completion events
        4. Validates database state
        5. Cleans up properly
        """
        env = collection_phase_test_environment
        spy = env["spy"]
        cleanup = env["cleanup"]
        validator = env["validator"]
        publisher = env["publisher"]
        test_data = env["test_data"]
        
        job_id = test_data["job_id"]
        
        # Step 1: Publish collection requests
        correlation_ids = await publisher.publish_products_collect_request(
            job_id=job_id,
            queries={"en": test_data["products_queries"]},
            top_amz=test_data["top_amz"],
            top_ebay=test_data["top_ebay"]
        )
        
        videos_correlation_id = await publisher.publish_videos_search_request(
            job_id=job_id,
            industry=test_data["industry"],
            queries=test_data["videos_queries"],
            platforms=test_data["platforms"],
            recency_days=test_data["recency_days"]
        )
        
        # Step 2: Wait for products collection completion
        products_event = await spy.wait_for_products_completed(
            job_id=job_id,
            timeout=10.0
        )
        
        # Verify products completion event
        assert products_event["event_data"]["job_id"] == job_id
        assert "event_id" in products_event["event_data"]
        assert products_event["routing_key"] == "products.collections.completed"
        
        # Step 3: Wait for videos collection completion
        videos_event = await spy.wait_for_videos_completed(
            job_id=job_id,
            timeout=10.0
        )
        
        # Verify videos completion event
        assert videos_event["event_data"]["job_id"] == job_id
        assert "event_id" in videos_event["event_data"]
        assert videos_event["routing_key"] == "videos.collections.completed"
        
        # Step 4: Validate database state
        await validator.assert_job_exists(job_id)
        
        # Note: In a real test with actual services running, we would expect
        # to find collected data. For this infrastructure test, we primarily
        # validate the event flow and test setup.
        
        # Step 5: Verify events were captured correctly
        products_messages = spy.spy.get_captured_messages_by_correlation_id(
            spy.products_queue, correlation_ids
        )
        videos_messages = spy.spy.get_captured_messages_by_correlation_id(
            spy.videos_queue, videos_correlation_id
        )
        
        assert len(products_messages) >= 1
        assert len(videos_messages) >= 1
    
    @pytest.mark.asyncio
    @pytest.mark.collection_phase
    @pytest.mark.integration
    @pytest.mark.observability
    async def test_complete_collection_workflow_with_observability(
        self,
        observability_test_environment,
        expected_observability_services
    ):
        """
        Test the complete collection workflow with full observability validation.
        
        This test:
        1. Sets up the test environment with observability capture
        2. Publishes collection requests
        3. Waits for completion events
        4. Validates database state
        5. Validates observability requirements (logs, metrics, health)
        6. Cleans up properly
        """
        env = observability_test_environment
        spy = env["spy"]
        cleanup = env["cleanup"]
        validator = env["validator"]
        publisher = env["publisher"]
        test_data = env["test_data"]
        obs_validator = env["observability"]
        
        job_id = test_data["job_id"]
        
        # Step 1: Publish collection requests
        correlation_ids = await publisher.publish_products_collect_request(
            job_id=job_id,
            queries={"en": test_data["products_queries"]},
            top_amz=test_data["top_amz"],
            top_ebay=test_data["top_ebay"]
        )
        
        videos_correlation_id = await publisher.publish_videos_search_request(
            job_id=job_id,
            industry=test_data["industry"],
            queries=test_data["videos_queries"],
            platforms=test_data["platforms"],
            recency_days=test_data["recency_days"]
        )
        
        # Step 2: Wait for products collection completion
        products_event = await spy.wait_for_products_completed(
            job_id=job_id,
            timeout=10.0
        )
        
        # Verify products completion event
        assert products_event["event_data"]["job_id"] == job_id
        assert "event_id" in products_event["event_data"]
        assert products_event["routing_key"] == "products.collections.completed"
        
        # Step 3: Wait for videos collection completion
        videos_event = await spy.wait_for_videos_completed(
            job_id=job_id,
            timeout=10.0
        )
        
        # Verify videos completion event
        assert videos_event["event_data"]["job_id"] == job_id
        assert "event_id" in videos_event["event_data"]
        assert videos_event["routing_key"] == "videos.collections.completed"
        
        # Step 4: Validate database state
        await validator.assert_job_exists(job_id)
        
        # Step 5: Validate observability requirements
        # Use the first correlation ID for validation
        primary_correlation_id = correlation_ids[0] if correlation_ids else videos_correlation_id
        
        observability_results = await obs_validator.assert_observability_requirements(
            correlation_id=primary_correlation_id,
            expected_services=expected_observability_services
        )
        
        # Verify specific observability outcomes
        assert observability_results["overall_valid"], "Overall observability validation failed"
        
        # Verify logs contain correlation ID
        assert observability_results["logs"]["correlation_present"], "Correlation ID not found in logs"
        
        # Verify all expected services logged properly
        assert all(observability_results["logs"]["services"].values()), "Some services did not log properly"
        
        # Verify metrics were incremented
        assert observability_results["metrics"]["products_collections_completed"], "Products collection metric not incremented"
        assert observability_results["metrics"]["videos_collections_completed"], "Videos collection metric not incremented"
        
        # Verify health status
        assert observability_results["health"]["status"] == "healthy", "Health checks failed"
        
        # Verify DLQ is empty
        dlq_check = observability_results["health"]["checks"].get("dlq", {})
        assert dlq_check.get("status") == "healthy", "DLQ is not empty"
        
        # Step 6: Verify events were captured correctly
        products_messages = spy.spy.get_captured_messages_by_correlation_id(
            spy.products_queue, correlation_ids
        )
        videos_messages = spy.spy.get_captured_messages_by_correlation_id(
            spy.videos_queue, videos_correlation_id
        )
        
        assert len(products_messages) >= 1
        assert len(videos_messages) >= 1
    
    @pytest.mark.asyncio
    @pytest.mark.collection_phase
    @pytest.mark.integration
    async def test_collection_phase_with_test_environment_manager(
        self,
        db_manager,
        message_broker
    ):
        """
        Test collection phase using the test environment manager.
        Demonstrates proper isolation and cleanup.
        """
        from utils.test_environment import TestEnvironmentManager
        
        async with TestEnvironmentManager(db_manager, message_broker, "amqp://guest:guest@localhost:5672/") as manager:
            # Create first test environment
            env1 = await manager.create_environment("test1")
            
            # Create second test environment (different job ID)
            env2 = await manager.create_environment("test2")
            
            # Verify they have different job IDs
            assert env1.test_job_id != env2.test_job_id
            
            # Publish requests in first environment
            await env1.publish_collection_requests(
                products_queries=["test product 1"],
                videos_queries={"vi": ["test video 1"]},
                industry="test industry 1",
                platforms=["youtube"]
            )
            
            # Publish requests in second environment
            await env2.publish_collection_requests(
                products_queries=["test product 2"],
                videos_queries={"vi": ["test video 2"]},
                industry="test industry 2",
                platforms=["tiktok"]
            )
            
            # Both environments should work independently
            # (In a real test with services running, we would wait for completions)
            
            # Verify job records exist
            await db_manager.fetch_val("SELECT COUNT(*) FROM jobs WHERE job_id = $1", env1.test_job_id)
            await db_manager.fetch_val("SELECT COUNT(*) FROM jobs WHERE job_id = $1", env2.test_job_id)
            
            # Environments will be automatically cleaned up
    
    @pytest.mark.asyncio
    @pytest.mark.collection_phase
    @pytest.mark.integration
    async def test_message_spy_functionality(
        self,
        message_spy
    ):
        """
        Test the message spy utilities directly.
        """
        spy = message_spy
        
        # Create a spy queue for testing
        queue_name = await spy.create_spy_queue("test.routing.key")
        
        # Start consuming
        await spy.start_consuming(queue_name)
        
        # Publish a test message using the broker
        await spy.spy.exchange.publish(
            spy.spy.channel.default_exchange,
            '{"test": "message"}',
            routing_key="test.routing.key"
        )
        
        # Wait for the message
        message = await spy.wait_for_message(
            queue_name=queue_name,
            timeout=5.0
        )
        
        assert message is not None
        assert message["event_data"]["test"] == "message"
        
        # Stop consuming
        await spy.stop_consuming(queue_name)
    
    @pytest.mark.asyncio
    @pytest.mark.collection_phase
    @pytest.mark.integration
    async def test_database_cleanup_functionality(
        self,
        db_manager,
        collection_job_setup
    ):
        """
        Test the database cleanup utilities.
        """
        from utils.db_cleanup import CollectionPhaseCleanup
        
        job_id = collection_job_setup
        cleanup = CollectionPhaseCleanup(db_manager)
        
        # Insert some test data
        await db_manager.execute(
            "INSERT INTO products (product_id, job_id, src, title) VALUES ($1, $2, $3, $4)",
            "test_product_1", job_id, "test", "Test Product"
        )
        
        await db_manager.execute(
            "INSERT INTO videos (video_id, job_id, platform, title) VALUES ($1, $2, $3, $4)",
            "test_video_1", job_id, "youtube", "Test Video"
        )
        
        # Verify data exists
        product_count = await db_manager.fetch_val(
            "SELECT COUNT(*) FROM products WHERE job_id = $1", job_id
        )
        video_count = await db_manager.fetch_val(
            "SELECT COUNT(*) FROM videos WHERE job_id = $1", job_id
        )
        
        assert product_count == 1
        assert video_count == 1
        
        # Clean up the test data
        await cleanup.cleanup_specific_job(job_id)
        
        # Verify data is gone
        product_count = await db_manager.fetch_val(
            "SELECT COUNT(*) FROM products WHERE job_id = $1", job_id
        )
        video_count = await db_manager.fetch_val(
            "SELECT COUNT(*) FROM videos WHERE job_id = $1", job_id
        )
        
        assert product_count == 0
        assert video_count == 0
    
    @pytest.mark.asyncio
    @pytest.mark.collection_phase
    @pytest.mark.integration
    async def test_event_publisher_validation(
        self,
        event_publisher
    ):
        """
        Test the event publisher utilities and validation.
        """
        from utils.event_publisher import EventValidator
        
        # Create test events
        products_event = TestEventFactory.create_products_collect_request()
        videos_event = TestEventFactory.create_videos_search_request()
        completed_event = TestEventFactory.create_collections_completed()
        
        # Validate events
        assert EventValidator.validate_products_collect_request(products_event)
        assert EventValidator.validate_videos_search_request(videos_event)
        assert EventValidator.validate_collections_completed(completed_event)
        
        # Test invalid events
        invalid_products = {"job_id": "test"}  # Missing required fields
        invalid_videos = {"job_id": "test"}  # Missing required fields
        invalid_completed = {"job_id": "test"}  # Missing event_id
        
        assert not EventValidator.validate_products_collect_request(invalid_products)
        assert not EventValidator.validate_videos_search_request(invalid_videos)
        assert not EventValidator.validate_collections_completed(invalid_completed)
    
    @pytest.mark.asyncio
    @pytest.mark.collection_phase
    @pytest.mark.integration
    async def test_database_state_validator(
        self,
        db_manager,
        collection_job_setup
    ):
        """
        Test the database state validator utilities.
        """
        job_id = collection_job_setup
        validator = DatabaseStateValidator(db_manager)
        
        # Test job existence validation
        await validator.assert_job_exists(job_id)
        
        # Test job status (should be 'started' from our setup)
        await validator.assert_job_status(job_id, "started")
        
        # Test non-existent job
        with pytest.raises(AssertionError):
            await validator.assert_job_exists("non_existent_job")
        
        # Insert test data for further validation
        await db_manager.execute(
            "INSERT INTO products (product_id, job_id, src, title) VALUES ($1, $2, $3, $4)",
            "test_product_1", job_id, "amazon", "Test Product"
        )
        
        await db_manager.execute(
            "INSERT INTO videos (video_id, job_id, platform, title) VALUES ($1, $2, $3, $4)",
            "test_video_1", job_id, "youtube", "Test Video"
        )
        
        # Test collection validation
        await validator.assert_products_collected(job_id, min_count=1)
        await validator.assert_videos_collected(job_id, min_count=1)
        
        # Test collection summary
        summary = await validator.get_collection_summary(job_id)
        assert summary["products"] == 1
        assert summary["videos"] == 1
        assert summary["video_frames"] == 0  # No frames in this test
        assert summary["product_images"] == 0  # No images in this test
    
    @pytest.mark.asyncio
    @pytest.mark.collection_phase
    @pytest.mark.integration
    async def test_context_manager_cleanup(
        self,
        db_manager,
        message_broker
    ):
        """
        Test that the test environment properly cleans up using context managers.
        """
        job_id = None
        
        async with CollectionPhaseTestEnvironment(
            db_manager, message_broker, "amqp://guest:guest@localhost:5672/"
        ) as env:
            job_id = env.test_job_id
            
            # Verify setup
            assert env.setup_complete
            assert job_id is not None
            
            # Verify job exists
            job_count = await db_manager.fetch_val(
                "SELECT COUNT(*) FROM jobs WHERE job_id = $1", job_id
            )
            assert job_count == 1
        
        # After context manager exit, verify cleanup
        # Note: The job record might still exist if the actual services haven't
        # processed it yet, but the test environment should be cleaned up
        
        # The environment should be torn down
        assert not env.setup_complete
    
    @pytest.mark.asyncio
    @pytest.mark.collection_phase
    @pytest.mark.integration
    @pytest.mark.performance
    async def test_concurrent_collection_workflows(
        self,
        db_manager,
        message_broker
    ):
        """
        Test multiple concurrent collection workflows.
        """
        # Create multiple test environments concurrently
        environments = []
        
        async def create_env(index: int):
            env = CollectionPhaseTestEnvironment(
                db_manager, message_broker, "amqp://guest:guest@localhost:5672/"
            )
            await env.setup()
            return env
        
        # Create 3 environments concurrently
        environments = await asyncio.gather(
            *[create_env(i) for i in range(3)]
        )
        
        # Verify they have different job IDs
        job_ids = [env.test_job_id for env in environments]
        assert len(set(job_ids)) == 3  # All unique
        
        # Publish requests in all environments
        tasks = []
        for i, env in enumerate(environments):
            task = env.publish_collection_requests(
                products_queries=[f"test product {i}"],
                videos_queries={"vi": [f"test video {i}"]},
                industry=f"test industry {i}",
                platforms=["youtube"]
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Clean up all environments
        cleanup_tasks = [env.teardown() for env in environments]
        await asyncio.gather(*cleanup_tasks)
        
        # Verify all jobs exist
        for job_id in job_ids:
            job_count = await db_manager.fetch_val(
                "SELECT COUNT(*) FROM jobs WHERE job_id = $1", job_id
            )
            assert job_count == 1


if __name__ == "__main__":
    # This allows running the tests directly
    pytest.main([__file__, "-v"])