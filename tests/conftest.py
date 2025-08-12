"""
Pytest configuration and fixtures for integration tests
"""
import pytest
import asyncio
import asyncpg
import httpx
import os
import sys
from pathlib import Path

# Add libs to path
sys.path.append(str(Path(__file__).parent.parent / "libs"))

from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_manager():
    """Database manager fixture"""
    dsn = os.getenv("POSTGRES_DSN", "postgresql://postgres:dev@localhost:5432/postgres")
    db = DatabaseManager(dsn)
    await db.connect()
    yield db
    await db.disconnect()


@pytest.fixture(scope="session")
async def message_broker():
    """Message broker fixture"""
    broker_url = os.getenv("BUS_BROKER", "amqp://guest:guest@localhost:5672/")
    broker = MessageBroker(broker_url)
    await broker.connect()
    yield broker
    await broker.disconnect()


@pytest.fixture(scope="session")
async def http_client():
    """HTTP client fixture"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest.fixture
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
    return os.getenv("MAIN_API_URL", "http://localhost:8000")


@pytest.fixture
def results_api_url():
    return os.getenv("RESULTS_API_URL", "http://localhost:8080")