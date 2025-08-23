"""
Test configuration and fixtures for the Results API service.
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from httpx import AsyncClient

from main import create_app
from core.config import Settings, DatabaseSettings, AppSettings, MCPSettings, reset_settings
from core.dependencies import DatabaseManagerSingleton
from services.results_service import ResultsService


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings"""
    return Settings(
        database=DatabaseSettings(
            dsn="postgresql://test:test@localhost:5432/test_db",
            pool_size=1,
            max_overflow=0,
            timeout=10
        ),
        app=AppSettings(
            title="Test Results API",
            version="1.0.0-test",
            debug=True,
            cors_origins="http://localhost:3000",
            log_level="DEBUG"
        ),
        mcp=MCPSettings(
            enabled=False,  # Disable MCP for tests
            title="Test MCP Server",
            description="Test MCP server",
            mount_path="/test-mcp"
        )
    )


@pytest.fixture
def mock_database():
    """Create a mock database manager"""
    mock_db = AsyncMock()
    mock_db.connect = AsyncMock()
    mock_db.disconnect = AsyncMock()
    mock_db.fetch_val = AsyncMock()
    mock_db.fetch_one = AsyncMock()
    mock_db.fetch_all = AsyncMock()
    return mock_db


@pytest.fixture
def mock_product_crud():
    """Create a mock product CRUD"""
    mock_crud = AsyncMock()
    mock_crud.get_product = AsyncMock()
    mock_crud.list_products = AsyncMock()
    return mock_crud


@pytest.fixture
def mock_video_crud():
    """Create a mock video CRUD"""
    mock_crud = AsyncMock()
    mock_crud.get_video = AsyncMock()
    mock_crud.list_videos = AsyncMock()
    return mock_crud


@pytest.fixture
def mock_match_crud():
    """Create a mock match CRUD"""
    mock_crud = AsyncMock()
    mock_crud.get_match = AsyncMock()
    mock_crud.list_matches = AsyncMock()
    return mock_crud


@pytest.fixture
def mock_results_service():
    """Create a mock results service"""
    service = AsyncMock(spec=ResultsService)
    service.get_results = AsyncMock()
    service.get_product = AsyncMock()
    service.get_video = AsyncMock()
    service.get_match = AsyncMock()
    service.get_evidence_path = AsyncMock()
    service.get_stats = AsyncMock()
    return service


@pytest.fixture
def test_app(test_settings, mock_results_service, monkeypatch):
    """Create a test FastAPI application"""
    # Reset settings singleton
    reset_settings()
    
    # Mock get_settings to return test settings
    monkeypatch.setattr("core.config.get_settings", lambda: test_settings)
    monkeypatch.setattr("core.dependencies.get_settings", lambda: test_settings)
    
    # Create test app
    app = create_app()
    
    # Override the results service dependency with our mock
    from core.dependencies import get_results_service
    app.dependency_overrides[get_results_service] = lambda: mock_results_service
    
    return app


@pytest.fixture
def test_client(test_app) -> TestClient:
    """Create a test client"""
    return TestClient(test_app)


@pytest.fixture
async def async_test_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client"""
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_product_data():
    """Sample product data for testing"""
    return {
        "product_id": "test-product-1",
        "src": "amazon",
        "asin_or_itemid": "B123456789",
        "title": "Test Product",
        "brand": "Test Brand",
        "url": "https://amazon.com/test-product",
        "created_at": "2024-01-01T00:00:00Z",
        "image_count": 5
    }


@pytest.fixture
def sample_video_data():
    """Sample video data for testing"""
    return {
        "video_id": "test-video-1",
        "platform": "youtube",
        "url": "https://youtube.com/watch?v=test",
        "title": "Test Video",
        "duration_s": 300,
        "published_at": "2024-01-01T00:00:00Z",
        "created_at": "2024-01-01T00:00:00Z",
        "frame_count": 100
    }


@pytest.fixture
def sample_match_data():
    """Sample match data for testing"""
    return {
        "match_id": "test-match-1",
        "job_id": "test-job-1",
        "product_id": "test-product-1",
        "video_id": "test-video-1",
        "best_img_id": "test-img-1",
        "best_frame_id": "test-frame-1",
        "ts": 120.5,
        "score": 0.85,
        "evidence_path": "/path/to/evidence.jpg",
        "created_at": "2024-01-01T00:00:00Z",
        "product_title": "Test Product",
        "video_title": "Test Video",
        "video_platform": "youtube"
    }


@pytest.fixture
def sample_stats_data():
    """Sample stats data for testing"""
    return {
        "products": 100,
        "product_images": 500,
        "videos": 50,
        "video_frames": 5000,
        "matches": 25,
        "jobs": 10
    }


# Mock database entities
class MockProduct:
    def __init__(self, **kwargs):
        self.product_id = kwargs.get("product_id", "test-product-1")
        self.src = kwargs.get("src", "amazon")
        self.asin_or_itemid = kwargs.get("asin_or_itemid", "B123456789")
        self.title = kwargs.get("title", "Test Product")
        self.brand = kwargs.get("brand", "Test Brand")
        self.url = kwargs.get("url", "https://amazon.com/test-product")
        self.created_at = kwargs.get("created_at")


class MockVideo:
    def __init__(self, **kwargs):
        self.video_id = kwargs.get("video_id", "test-video-1")
        self.platform = kwargs.get("platform", "youtube")
        self.url = kwargs.get("url", "https://youtube.com/watch?v=test")
        self.title = kwargs.get("title", "Test Video")
        self.duration_s = kwargs.get("duration_s", 300)
        self.published_at = kwargs.get("published_at")
        self.created_at = kwargs.get("created_at")


class MockMatch:
    def __init__(self, **kwargs):
        self.match_id = kwargs.get("match_id", "test-match-1")
        self.job_id = kwargs.get("job_id", "test-job-1")
        self.product_id = kwargs.get("product_id", "test-product-1")
        self.video_id = kwargs.get("video_id", "test-video-1")
        self.best_img_id = kwargs.get("best_img_id", "test-img-1")
        self.best_frame_id = kwargs.get("best_frame_id", "test-frame-1")
        self.ts = kwargs.get("ts", 120.5)
        self.score = kwargs.get("score", 0.85)
        self.evidence_path = kwargs.get("evidence_path", "/path/to/evidence.jpg")
        self.created_at = kwargs.get("created_at")


@pytest.fixture
def mock_product():
    """Create a mock product entity"""
    return MockProduct()


@pytest.fixture
def mock_video():
    """Create a mock video entity"""
    return MockVideo()


@pytest.fixture
def mock_match():
    """Create a mock match entity"""
    return MockMatch()