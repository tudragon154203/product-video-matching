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

# Add libs to path
sys.path.append(str(Path(__file__).parent.parent / "libs"))
sys.path.append(str(Path(__file__).parent.parent / "infra"))
sys.path.append(str(Path(__file__).parent.parent))

from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from config import config


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


@pytest.fixture
def results_api_url():
    return config.RESULTS_API_URL