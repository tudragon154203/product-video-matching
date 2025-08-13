import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from service import CatalogCollectorService
from collectors import AmazonProductCollector, EbayProductCollector


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_broker():
    return AsyncMock()


@pytest.fixture
def service(mock_db, mock_broker):
    return CatalogCollectorService(mock_db, mock_broker, "./data")


@pytest.mark.asyncio
async def test_handle_products_collect_request(service):
    # Arrange
    event_data = {
        "job_id": "test-job-123",
        "top_amz": 2,
        "top_ebay": 2,
        "queries": {
            "en": ["test query"]
        }
    }

    # Create mock collectors
    mock_amazon_collector = Mock()
    mock_amazon_collector.collect_products = AsyncMock(return_value=[])
    mock_ebay_collector = Mock()
    mock_ebay_collector.collect_products = AsyncMock(return_value=[])

    # Replace the collectors in the service
    service.collectors["amazon"] = mock_amazon_collector
    service.collectors["ebay"] = mock_ebay_collector

    # Act
    await service.handle_products_collect_request(event_data)

    # Assert
    # Verify that collect_products was called for both Amazon and eBay
    mock_amazon_collector.collect_products.assert_called_once_with("test query", 2)
    mock_ebay_collector.collect_products.assert_called_once_with("test query", 2)


@pytest.mark.asyncio
async def test_amazon_collector_get_source_name():
    collector = AmazonProductCollector("./data")
    assert collector.get_source_name() == "amazon"


@pytest.mark.asyncio
async def test_ebay_collector_get_source_name():
    collector = EbayProductCollector("./data")
    assert collector.get_source_name() == "ebay"