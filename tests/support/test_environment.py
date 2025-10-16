"""
Test environment setup and cleanup utilities for collection phase integration tests.
Provides comprehensive test environment management with proper isolation.
"""
import asyncio
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from common_py.logging_config import configure_logging

from .message_spy import CollectionPhaseSpy
from .db_cleanup import CollectionPhaseCleanup
from .event_publisher import CollectionEventPublisher

logger = configure_logging("test-utils:test-environment")


class CollectionPhaseTestEnvironment:
    """
    Complete test environment manager for collection phase integration tests.
    Handles setup, execution, and cleanup with proper isolation.
    """
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        message_broker: MessageBroker,
        broker_url: str,
        timeout_per_event: float = 10.0
    ):
        self.db_manager = db_manager
        self.message_broker = message_broker
        self.broker_url = broker_url
        self.timeout_per_event = timeout_per_event
        
        # Test components
        self.spy = None
        self.cleanup = None
        self.publisher = None
        
        # Test state
        self.test_job_id = None
        self.setup_complete = False
        self.temp_dirs = []
        
    async def setup(self, job_id: Optional[str] = None):
        """
        Set up the complete test environment.
        
        Args:
            job_id: Optional job ID for the test (auto-generated if not provided)
        """
        if self.setup_complete:
            raise RuntimeError("Test environment already set up")
        
        try:
            # Generate test job ID if not provided
            if not job_id:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                self.test_job_id = f"test_job_{timestamp}_{os.getpid()}"
            else:
                self.test_job_id = job_id
            
            logger.info("Setting up collection phase test environment", job_id=self.test_job_id)
            
            # Initialize components
            self.spy = CollectionPhaseSpy(self.broker_url)
            self.cleanup = CollectionPhaseCleanup(self.db_manager)
            self.publisher = CollectionEventPublisher(self.message_broker)
            
            # Connect spy
            await self.spy.connect()
            
            # Clear any existing messages
            self.spy.clear_messages()
            
            # Clean up any existing test data
            await self.cleanup.cleanup_test_data()
            
            # Create test job record
            await self._create_test_job()
            
            self.setup_complete = True
            
            logger.info("Collection phase test environment setup complete", job_id=self.test_job_id)
            
        except Exception as e:
            logger.error("Failed to set up test environment", error=str(e))
            await self.teardown()
            raise
    
    async def teardown(self):
        """Clean up the test environment"""
        if not self.setup_complete:
            return
        
        logger.info("Tearing down collection phase test environment", job_id=self.test_job_id)
        
        try:
            # Clean up test data
            if self.cleanup and self.test_job_id:
                await self.cleanup.cleanup_specific_job(self.test_job_id)
            
            # Disconnect spy
            if self.spy:
                await self.spy.disconnect()
            
            # Clear published events
            if self.publisher:
                self.publisher.clear_published_events()
            
            # Clean up temporary directories
            for temp_dir in self.temp_dirs:
                try:
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception as e:
                    logger.warning("Failed to clean up temp directory", dir=temp_dir, error=str(e))
            
            self.temp_dirs.clear()
            
        except Exception as e:
            logger.error("Error during test environment teardown", error=str(e))
        
        finally:
            self.setup_complete = False
            self.test_job_id = None
    
    async def _create_test_job(self):
        """Create a test job record in the database (idempotent)."""
        await self.db_manager.execute(
            """
            INSERT INTO jobs (job_id, industry, phase, created_at, updated_at)
            VALUES ($1, $2, $3, NOW(), NOW())
            ON CONFLICT (job_id) DO NOTHING;
            """,
            self.test_job_id,
            "test industry",
            "collection",
        )

        logger.debug("Created test job record", job_id=self.test_job_id)
    
    async def publish_collection_requests(
        self,
        products_queries: List[str],
        videos_queries: Dict[str, List[str]],
        industry: str,
        platforms: List[str],
        top_amz: int = 20,
        top_ebay: int = 20,
        recency_days: int = 30
    ) -> Dict[str, str]:
        """
        Publish both products and videos collection requests.
        
        Args:
            products_queries: List of product search queries
            videos_queries: Dict of video search queries by language
            industry: Industry keyword for video search
            platforms: List of video platforms
            top_amz: Number of Amazon products to collect
            top_ebay: Number of eBay products to collect
            recency_days: Recency in days for video search
            
        Returns:
            Dictionary with correlation IDs for both requests
        """
        if not self.setup_complete:
            raise RuntimeError("Test environment not set up")
        
        # Publish products collect request
        products_correlation_id = await self.publisher.publish_products_collect_request(
            job_id=self.test_job_id,
            queries={"en": products_queries},
            top_amz=top_amz,
            top_ebay=top_ebay
        )
        
        # Publish videos search request
        videos_correlation_id = await self.publisher.publish_videos_search_request(
            job_id=self.test_job_id,
            industry=industry,
            queries=videos_queries,
            platforms=platforms,
            recency_days=recency_days
        )
        
        logger.info(
            "Published collection requests",
            job_id=self.test_job_id,
            products_correlation_id=products_correlation_id,
            videos_correlation_id=videos_correlation_id
        )
        
        return {
            "products": products_correlation_id,
            "videos": videos_correlation_id
        }
    
    async def wait_for_collection_completion(
        self,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Wait for both products and videos collection completion events.
        
        Args:
            timeout: Optional timeout (uses default if not provided)
            
        Returns:
            Dictionary with completion events
        """
        if not self.setup_complete:
            raise RuntimeError("Test environment not set up")
        
        timeout = timeout or (self.timeout_per_event * 2)
        
        logger.info(
            "Waiting for collection completion",
            job_id=self.test_job_id,
            timeout=timeout
        )
        
        completion_events = await self.spy.wait_for_both_completed(
            job_id=self.test_job_id,
            timeout=timeout
        )
        
        logger.info(
            "Collection completion received",
            job_id=self.test_job_id,
            products_event_id=completion_events["products"]["event_data"]["event_id"],
            videos_event_id=completion_events["videos"]["event_data"]["event_id"]
        )
        
        return completion_events
    
    async def verify_collection_results(
        self,
        min_products: int = 1,
        min_videos: int = 1
    ) -> Dict[str, int]:
        """
        Verify that collection results exist in the database.
        
        Args:
            min_products: Minimum number of products expected
            min_videos: Minimum number of videos expected
            
        Returns:
            Dictionary with collection counts
        """
        if not self.setup_complete:
            raise RuntimeError("Test environment not set up")
        
        # Count products
        products_count = await self.db_manager.fetch_val(
            "SELECT COUNT(*) FROM products WHERE job_id = $1",
            self.test_job_id
        )
        
        # Count videos
        videos_count = await self.db_manager.fetch_val(
            "SELECT COUNT(*) FROM videos WHERE job_id = $1",
            self.test_job_id
        )
        
        results = {
            "products": products_count,
            "videos": videos_count
        }
        
        # Verify minimum counts
        if products_count < min_products:
            raise AssertionError(
                f"Expected at least {min_products} products, found {products_count}"
            )
        
        if videos_count < min_videos:
            raise AssertionError(
                f"Expected at least {min_videos} videos, found {videos_count}"
            )
        
        logger.info(
            "Collection results verified",
            job_id=self.test_job_id,
            results=results
        )
        
        return results
    
    def create_temp_directory(self) -> str:
        """
        Create a temporary directory for the test.
        
        Returns:
            Path to the temporary directory
        """
        temp_dir = tempfile.mkdtemp(prefix=f"collection_test_{self.test_job_id}_")
        self.temp_dirs.append(temp_dir)
        
        logger.debug("Created temporary directory", dir=temp_dir)
        return temp_dir
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.setup()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.teardown()


class TestEnvironmentManager:
    """
    Manager for multiple test environments with proper isolation.
    """
    
    def __init__(self, db_manager: DatabaseManager, message_broker: MessageBroker, broker_url: str):
        self.db_manager = db_manager
        self.message_broker = message_broker
        self.broker_url = broker_url
        self.environments = {}
    
    async def create_environment(
        self,
        name: str,
        job_id: Optional[str] = None,
        timeout_per_event: float = 10.0
    ) -> CollectionPhaseTestEnvironment:
        """
        Create a new test environment.
        
        Args:
            name: Name for the environment
            job_id: Optional job ID
            timeout_per_event: Timeout per event in seconds
            
        Returns:
            Created test environment
        """
        if name in self.environments:
            raise ValueError(f"Test environment '{name}' already exists")
        
        environment = CollectionPhaseTestEnvironment(
            db_manager=self.db_manager,
            message_broker=self.message_broker,
            broker_url=self.broker_url,
            timeout_per_event=timeout_per_event
        )

        # Generate a unique job_id if not provided
        if job_id is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
            unique_suffix = os.urandom(2).hex()
            generated_job_id = f"test_job_{timestamp}_{os.getpid()}_{name}_{unique_suffix}"
        else:
            generated_job_id = job_id

        await environment.setup(generated_job_id)
        
        self.environments[name] = environment
        
        logger.info("Created test environment", name=name, job_id=environment.test_job_id)
        
        return environment
    
    async def cleanup_environment(self, name: str):
        """
        Clean up a specific test environment.
        
        Args:
            name: Name of the environment to clean up
        """
        if name not in self.environments:
            return
        
        environment = self.environments[name]
        await environment.teardown()
        
        del self.environments[name]
        
        logger.info("Cleaned up test environment", name=name)
    
    async def cleanup_all_environments(self):
        """Clean up all test environments"""
        for name in list(self.environments.keys()):
            await self.cleanup_environment(name)
        
        logger.info("Cleaned up all test environments")
    
    def get_environment(self, name: str) -> Optional[CollectionPhaseTestEnvironment]:
        """Get a test environment by name"""
        return self.environments.get(name)
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup_all_environments()


async def setup_collection_test_stack(
    db_manager: DatabaseManager,
    message_broker: MessageBroker,
    broker_url: str
) -> CollectionPhaseTestEnvironment:
    """
    Convenience function to set up a collection test environment.
    
    Args:
        db_manager: Database manager
        message_broker: Message broker
        broker_url: RabbitMQ broker URL
        
    Returns:
        Set up test environment
    """
    env = CollectionPhaseTestEnvironment(db_manager, message_broker, broker_url)
    await env.setup()
    return env