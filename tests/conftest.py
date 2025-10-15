"""
Pytest configuration and fixtures for integration tests
"""
import pytest
import pytest_asyncio
import asyncio
import asyncpg
import httpx
import os
import sys
from pathlib import Path

# Add project paths to sys.path for tests
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LIBS_DIR = PROJECT_ROOT / "libs"
COMMON_PY_DIR = LIBS_DIR / "common-py"
INFRA_DIR = PROJECT_ROOT / "infra"

def ensure_sys_path():
    """Ensure project-specific paths are available for imports."""
    for path in (COMMON_PY_DIR, LIBS_DIR, INFRA_DIR, PROJECT_ROOT):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.append(path_str)

    # Propagate to PYTHONPATH so subprocesses inherit the same paths
    pythonpath = os.environ.get("PYTHONPATH", "")
    paths = [str(COMMON_PY_DIR), str(LIBS_DIR)]
    merged = os.pathsep.join(
        [p for p in paths + pythonpath.split(os.pathsep) if p]
    )
    os.environ["PYTHONPATH"] = merged


ensure_sys_path()

from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from config import config

# Import test utilities
from support.message_spy import CollectionPhaseSpy, MessageSpy
from support.db_cleanup import CollectionPhaseCleanup, DatabaseStateValidator
from support.event_publisher import CollectionEventPublisher, TestEventFactory
from support.observability_validator import ObservabilityValidator, LogCapture, MetricsCapture


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_manager():
    """Database manager fixture"""
    dsn = config.POSTGRES_DSN
    db = DatabaseManager(dsn)
    await db.connect()
    yield db
    await db.disconnect()


@pytest_asyncio.fixture(scope="session")
async def message_broker():
    """Message broker fixture"""
    broker_url = config.BUS_BROKER
    broker = MessageBroker(broker_url)
    await broker.connect()
    yield broker
    await broker.disconnect()


@pytest_asyncio.fixture(scope="session")
async def http_client():
    """HTTP client fixture"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        yield client


@pytest_asyncio.fixture
async def clean_database(db_manager):
    """Clean database before each test"""
    # Clean up test data
    await db_manager.execute("DELETE FROM matches WHERE job_id LIKE 'test_%'")
    await db_manager.execute("DELETE FROM video_frames WHERE video_id IN (SELECT video_id FROM videos WHERE job_id LIKE 'test_%')")
    await db_manager.execute("DELETE FROM product_images WHERE product_id IN (SELECT product_id FROM products WHERE job_id LIKE 'test_%')")
    await db_manager.execute("DELETE FROM videos WHERE job_id LIKE 'test_%'")
    await db_manager.execute("DELETE FROM products WHERE job_id LIKE 'test_%'")
    await db_manager.execute("DELETE FROM jobs WHERE job_id LIKE 'test_%'")
    yield
    # Clean up after test
    await db_manager.execute("DELETE FROM matches WHERE job_id LIKE 'test_%'")
    await db_manager.execute("DELETE FROM video_frames WHERE video_id IN (SELECT video_id FROM videos WHERE job_id LIKE 'test_%')")
    await db_manager.execute("DELETE FROM product_images WHERE product_id IN (SELECT product_id FROM products WHERE job_id LIKE 'test_%')")
    await db_manager.execute("DELETE FROM videos WHERE job_id LIKE 'test_%'")
    await db_manager.execute("DELETE FROM products WHERE job_id LIKE 'test_%'")
    await db_manager.execute("DELETE FROM jobs WHERE job_id LIKE 'test_%'")


@pytest.fixture
def test_data():
    """Common test data"""
    return {
        "job_id": "test_job_123",
        "industry": "test pillows",
        "product": {
            "product_id": "test_product_1",
            "src": "amazon",
            "asin_or_itemid": "TEST123",
            "title": "Test Ergonomic Pillow",
            "brand": "TestBrand",
            "url": "https://example.com/product"
        },
        "video": {
            "video_id": "test_video_1",
            "platform": "youtube",
            "url": "https://youtube.com/watch?v=test123",
            "title": "Test Pillow Review",
            "duration_s": 180
        }
    }


# Service URL fixtures
@pytest.fixture
def main_api_url():
    return config.MAIN_API_URL


# Collection Phase Test Fixtures

@pytest_asyncio.fixture
async def collection_phase_spy(message_broker):
    """Collection phase message spy fixture"""
    spy = CollectionPhaseSpy(config.BUS_BROKER)
    await spy.connect()
    yield spy
    await spy.disconnect()


@pytest_asyncio.fixture
async def message_spy(message_broker):
    """Generic message spy fixture"""
    spy = MessageSpy(config.BUS_BROKER)
    await spy.connect()
    yield spy
    await spy.disconnect()


@pytest_asyncio.fixture
async def collection_cleanup(db_manager):
    """Collection phase database cleanup fixture"""
    cleanup = CollectionPhaseCleanup(db_manager)
    
    # Clean up before test
    await cleanup.cleanup_test_data()
    
    yield cleanup
    
    # Clean up after test
    await cleanup.cleanup_test_data()


@pytest_asyncio.fixture
async def db_validator(db_manager):
    """Database state validator fixture"""
    return DatabaseStateValidator(db_manager)


@pytest_asyncio.fixture
async def event_publisher(message_broker):
    """Collection event publisher fixture"""
    publisher = CollectionEventPublisher(message_broker)
    
    yield publisher
    
    # Clear published events tracking
    publisher.clear_published_events()


@pytest.fixture
def test_event_factory():
    """Test event factory fixture"""
    return TestEventFactory()


@pytest.fixture
def collection_test_data():
    """Collection phase test data fixture"""
    return {
        "job_id": TestEventFactory.create_test_job_id(),
        "industry": "test pillows",
        "products_queries": ["ergonomic pillows", "memory foam cushions"],
        "videos_queries": {
            "vi": ["gối ngủ ergonomics", "đánh giá gối memory foam"],
            "zh": ["人体工学枕头", "记忆泡沫枕头测评"]
        },
        "platforms": ["youtube", "tiktok"],
        "top_amz": 20,
        "top_ebay": 20,
        "recency_days": 30
    }


@pytest_asyncio.fixture
async def collection_phase_test_environment(
    collection_phase_spy,
    collection_cleanup,
    db_validator,
    event_publisher,
    test_event_factory,
    collection_test_data
):
    """
    Complete collection phase test environment fixture.
    Provides all necessary components for collection phase integration testing.
    """
    # Clear any existing messages
    collection_phase_spy.clear_messages()
    
    # Ensure clean database state
    await collection_cleanup.cleanup_test_data()
    
    yield {
        "spy": collection_phase_spy,
        "cleanup": collection_cleanup,
        "validator": db_validator,
        "publisher": event_publisher,
        "factory": test_event_factory,
        "test_data": collection_test_data
    }
    
    # Final cleanup
    await collection_cleanup.cleanup_test_data()


@pytest.fixture
def mock_products_collect_request(collection_test_data):
    """Mock products collect request event data"""
    return TestEventFactory.create_products_collect_request(
        job_id=collection_test_data["job_id"],
        queries=collection_test_data["products_queries"],
        top_amz=collection_test_data["top_amz"],
        top_ebay=collection_test_data["top_ebay"]
    )


@pytest.fixture
def mock_videos_search_request(collection_test_data):
    """Mock videos search request event data"""
    return TestEventFactory.create_videos_search_request(
        job_id=collection_test_data["job_id"],
        industry=collection_test_data["industry"],
        queries=collection_test_data["videos_queries"],
        platforms=collection_test_data["platforms"],
        recency_days=collection_test_data["recency_days"]
    )


@pytest_asyncio.fixture
async def collection_job_setup(db_manager, collection_test_data):
    """
    Set up a collection job in the database for testing.
    Creates a job record and returns the job ID.
    """
    job_id = collection_test_data["job_id"]
    
    # Insert job record
    await db_manager.execute(
        """
        INSERT INTO jobs (job_id, status, created_at, updated_at)
        VALUES ($1, 'started', NOW(), NOW())
        """,
        job_id
    )
    
    yield job_id
    
    # Clean up the job
    await db_manager.execute("DELETE FROM jobs WHERE job_id = $1", job_id)


# Observability Test Fixtures

@pytest_asyncio.fixture
async def log_capture():
    """Log capture fixture for testing"""
    capture = LogCapture()
    capture.start_capture()
    yield capture
    capture.stop_capture()


@pytest_asyncio.fixture
async def metrics_capture():
    """Metrics capture fixture for testing"""
    capture = MetricsCapture()
    capture.start_capture()
    yield capture
    capture.stop_capture()


@pytest_asyncio.fixture
async def observability_validator(db_manager, message_broker):
    """Observability validator fixture"""
    validator = ObservabilityValidator(db_manager, message_broker)
    yield validator
    # Clean up any remaining captures
    if validator.is_capturing:
        validator.stop_observability_capture()
    validator.clear_all_captures()


@pytest_asyncio.fixture
async def observability_test_environment(
    collection_phase_test_environment,
    observability_validator
):
    """
    Enhanced collection phase test environment with observability validation.
    Combines the existing test environment with observability capture and validation.
    """
    env = collection_phase_test_environment
    obs_validator = observability_validator
    
    # Start observability capture
    obs_validator.start_observability_capture()
    
    yield {
        **env,  # Include all existing environment components
        "observability": obs_validator
    }
    
    # Stop observability capture
    obs_validator.stop_observability_capture()


@pytest.fixture
def expected_observability_services():
    """Expected services for observability validation"""
    return [
        "main-api",
        "video-crawler",
        "vision-embedding",
        "vision-keypoint",
        "matcher"
    ]


@pytest_asyncio.fixture
async def collection_phase_with_observability(
    db_manager,
    message_broker,
    observability_validator,
    collection_test_data
):
    """
    Complete collection phase test with observability validation.
    Sets up the full collection workflow with observability monitoring.
    """
    # Set up observability capture
    observability_validator.start_observability_capture()
    
    # Create test job
    job_id = collection_test_data["job_id"]
    await db_manager.execute(
        """
        INSERT INTO jobs (job_id, status, created_at, updated_at)
        VALUES ($1, 'started', NOW(), NOW())
        """,
        job_id
    )
    
    yield {
        "job_id": job_id,
        "test_data": collection_test_data,
        "observability": observability_validator,
        "db_manager": db_manager,
        "message_broker": message_broker
    }
    
    # Clean up
    await db_manager.execute("DELETE FROM jobs WHERE job_id = $1", job_id)
    observability_validator.stop_observability_capture()
    observability_validator.clear_all_captures()

