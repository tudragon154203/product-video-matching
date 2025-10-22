"""
Pytest configuration and fixtures for integration tests
"""
# Early sys.path setup to resolve project modules when running from repo root

from support.spy.feature_extraction_spy import FeatureExtractionSpy
from support.validators.observability_validator import ObservabilityValidator
from support.publisher.event_publisher import CollectionEventPublisher, TestEventFactory, FeatureExtractionEventPublisher
from support.validators.db_cleanup import CollectionPhaseCleanup, DatabaseStateValidator, FeatureExtractionCleanup, FeatureExtractionStateValidator
from support.spy.message_spy import CollectionPhaseSpy, MessageSpy
from common_py.messaging import MessageBroker
from common_py.database import DatabaseManager
import pytest
import pytest_asyncio
import asyncio
import httpx
import os
import sys
from pathlib import Path

# Compute and add project paths BEFORE any project imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LIBS_DIR = PROJECT_ROOT / "libs"
COMMON_PY_DIR = LIBS_DIR / "common-py"
INFRA_DIR = PROJECT_ROOT / "infra"
TESTS_DIR = PROJECT_ROOT / "tests"


def _early_sys_path_setup():
    """Ensure project-specific paths are available before project imports."""
    for p in (COMMON_PY_DIR, LIBS_DIR, INFRA_DIR, PROJECT_ROOT, TESTS_DIR):
        ps = str(p)
        if ps in sys.path:
            continue
        # Prepend to prioritize our project paths
        sys.path.insert(0, ps)
    # Propagate to PYTHONPATH so subprocesses inherit the same paths
    pythonpath = os.environ.get("PYTHONPATH", "")
    paths = [str(COMMON_PY_DIR), str(LIBS_DIR), str(TESTS_DIR), str(PROJECT_ROOT)]
    merged = os.pathsep.join([p for p in paths + pythonpath.split(os.pathsep) if p])
    os.environ["PYTHONPATH"] = merged


_early_sys_path_setup()

# Minimal diagnostics to validate path setup and config import during collection
try:
    from config import config
    _cfg_mod = sys.modules.get("config")
    if _cfg_mod and getattr(_cfg_mod, "__file__", None):
        print(f"[conftest] config loaded from: {_cfg_mod.__file__}")
except Exception as e:
    print(f"[conftest] ERROR importing config: {e}")
    raise

# Third-party imports and project modules (safe after path setup)


@pytest_asyncio.fixture
async def observability_test_environment(
    collection_phase_spy,
    collection_cleanup,
    db_validator,
    event_publisher,
    test_event_factory,
    collection_test_data,
    db_manager,
    message_broker
):
    """
    Complete collection phase test environment with observability capture.
    Provides spy, cleanup, validator, publisher, test data, and an ObservabilityValidator.
    Ensures the job record exists before publishing requests.
    """
    # Initialize observability capture
    obs_validator = ObservabilityValidator(db_manager, message_broker)
    obs_validator.start_observability_capture()

    # Clear any existing messages and ensure clean DB state
    collection_phase_spy.clear_messages()
    await collection_cleanup.cleanup_test_data()

    # Create test job record (idempotent)
    job_id = collection_test_data["job_id"]
    await db_manager.execute(
        """
        INSERT INTO jobs (job_id, industry, phase, created_at, updated_at)
        VALUES ($1, 'test industry', 'collection', NOW(), NOW())
        ON CONFLICT (job_id) DO NOTHING;
        """,
        job_id
    )

    yield {
        "spy": collection_phase_spy,
        "cleanup": collection_cleanup,
        "validator": db_validator,
        "publisher": event_publisher,
        "factory": test_event_factory,
        "test_data": collection_test_data,
        "observability": obs_validator
    }

    # Stop capture and clean up
    try:
        obs_validator.stop_observability_capture()
        obs_validator.clear_all_captures()
    finally:
        await collection_cleanup.cleanup_test_data()


@pytest.fixture
def expected_observability_services():
    """
    Expected services that should produce logs conforming to standards during collection phase.
    Include both products and videos pipeline services.
    """
    return [
        "main-api",
        "dropship-product-finder",
        "video-crawler",
        "vision-embedding",
        "vision-keypoint",
        "matcher",
    ]


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
    # Clean up test data with error handling for corrupted data
    tables_to_clean = [
        ("matches", "job_id"),
        ("video_frames", "video_id"),
        ("product_images", "product_id"),
        ("videos", "job_id"),
        ("products", "job_id"),
        ("processed_events", "event_id"),
        ("phase_events", "job_id"),
        ("jobs", "job_id"),
    ]
    
    for table, id_column in tables_to_clean:
        try:
            if table == "video_frames":
                await db_manager.execute(
                    f"DELETE FROM {table} WHERE video_id IN (SELECT video_id FROM videos WHERE job_id LIKE 'test_%')"
                )
            elif table == "product_images":
                await db_manager.execute(
                    f"DELETE FROM {table} WHERE product_id IN (SELECT product_id FROM products WHERE job_id LIKE 'test_%')"
                )
            elif table == "processed_events":
                await db_manager.execute(
                    f"DELETE FROM {table} WHERE event_id LIKE 'test_%' OR event_id LIKE 'idempotency_test_%'"
                )
            else:
                await db_manager.execute(f"DELETE FROM {table} WHERE {id_column} LIKE 'test_%'")
        except Exception as e:
            # Log but don't fail on cleanup errors (e.g., corrupted data)
            print(f"Warning: Failed to clean {table}: {e}")
    
    yield
    
    # Clean up after test with same error handling
    for table, id_column in tables_to_clean:
        try:
            if table == "video_frames":
                await db_manager.execute(
                    f"DELETE FROM {table} WHERE video_id IN (SELECT video_id FROM videos WHERE job_id LIKE 'test_%')"
                )
            elif table == "product_images":
                await db_manager.execute(
                    f"DELETE FROM {table} WHERE product_id IN (SELECT product_id FROM products WHERE job_id LIKE 'test_%')"
                )
            elif table == "processed_events":
                await db_manager.execute(
                    f"DELETE FROM {table} WHERE event_id LIKE 'test_%' OR event_id LIKE 'idempotency_test_%'"
                )
            else:
                await db_manager.execute(f"DELETE FROM {table} WHERE {id_column} LIKE 'test_%'")
        except Exception as e:
            print(f"Warning: Failed to clean {table}: {e}")


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
        "platforms": ["tiktok"],  # TikTok only (faster)
        "top_amz": 0,  # Skip Amazon (faster)
        "top_ebay": 5,  # eBay only
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

    # Create test job record for this environment (idempotent)
    job_id = collection_test_data["job_id"]
    await collection_cleanup.db_manager.execute(
        """
        INSERT INTO jobs (job_id, industry, phase, created_at, updated_at)
        VALUES ($1, 'test industry', 'collection', NOW(), NOW())
        ON CONFLICT (job_id) DO NOTHING;
        """,
        job_id
    )
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
        INSERT INTO jobs (job_id, industry, phase, created_at, updated_at)
        VALUES ($1, 'test industry', 'collection', NOW(), NOW())
        """,
        job_id
    )

    yield job_id

    # Clean up the job
    await db_manager.execute("DELETE FROM jobs WHERE job_id = $1", job_id)


@pytest_asyncio.fixture
async def observability_validator(db_manager, message_broker):
    """Observability validator fixture"""
    return ObservabilityValidator(db_manager, message_broker)
