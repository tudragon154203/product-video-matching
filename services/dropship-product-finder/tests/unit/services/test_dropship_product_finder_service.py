"""
Unit tests for DropshipProductFinderService.
"""

from collectors.mock_ebay_collector import MockEbayCollector
from collectors.ebay.ebay_product_collector import EbayProductCollector
from collectors.amazon_product_collector import AmazonProductCollector
from collectors.base_product_collector import BaseProductCollector
from services.image_storage_manager import ImageStorageManager
from services.product_collection_manager import ProductCollectionManager
from services.service import DropshipProductFinderService
import uuid
import sys
import os
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add the parent directory to the path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_database_manager():
    """Mock DatabaseManager"""
    db = Mock()
    db.fetch_val = AsyncMock(return_value=5)  # Default: 5 images found
    db.fetch_all = AsyncMock(return_value=[
        {"img_id": "img_1", "product_id": "prod_1", "local_path": "/path/to/img_1"},
        {"img_id": "img_2", "product_id": "prod_1", "local_path": "/path/to/img_2"},
    ])
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_message_broker():
    """Mock MessageBroker"""
    broker = AsyncMock()
    broker.publish_event = AsyncMock()
    return broker


@pytest.fixture
def mock_config():
    """Mock configuration"""
    config = Mock()
    config.USE_MOCK_FINDERS = True
    return config


@pytest.fixture
def mock_collectors():
    """Mock collectors"""
    collectors = {
        "amazon": Mock(spec=AmazonProductCollector),
        "ebay": Mock(spec=MockEbayCollector),
    }
    # Add the missing update_redis_client method to MockEbayCollector
    collectors["ebay"].update_redis_client = Mock()
    return collectors


@pytest.fixture
def mock_image_storage_manager(mock_database_manager, mock_message_broker, mock_collectors):
    """Mock ImageStorageManager"""
    with patch("services.service.ImageStorageManager") as mock_manager_class:
        mock_manager = Mock(spec=ImageStorageManager)
        mock_manager.publish_individual_image_events = AsyncMock()
        mock_manager_class.return_value = mock_manager
        yield mock_manager


@pytest.fixture
def mock_product_collection_manager(mock_collectors, mock_image_storage_manager):
    """Mock ProductCollectionManager"""
    with patch("services.service.ProductCollectionManager") as mock_manager_class:
        mock_manager = Mock(spec=ProductCollectionManager)
        mock_manager.collect_and_store_products = AsyncMock(return_value=(2, 3))  # 2 amazon, 3 ebay
        mock_manager_class.return_value = mock_manager
        yield mock_manager


@pytest.fixture
def dropship_service(
    mock_database_manager,
    mock_message_broker,
    mock_config,
    mock_collectors,
    mock_image_storage_manager,
    mock_product_collection_manager,
):
    """Create DropshipProductFinderService with mocked dependencies"""
    with patch("services.service.config", mock_config):
        with patch("services.service.ImageStorageManager", return_value=mock_image_storage_manager):
            with patch("services.service.ProductCollectionManager", return_value=mock_product_collection_manager):
                service = DropshipProductFinderService(
                    db=mock_database_manager,
                    broker=mock_message_broker,
                    data_root="/tmp/test",
                    redis_client=None,
                )
                return service


class TestDropshipProductFinderService:
    """Test cases for DropshipProductFinderService"""

    @pytest.mark.asyncio
    async def test_init_with_mock_finders(self, mock_config, mock_database_manager, mock_message_broker):
        """Test initialization with USE_MOCK_FINDERS=True"""
        with patch("services.service.config", mock_config):
            with patch("services.service.ImageStorageManager") as mock_image_manager_class:
                with patch("services.service.ProductCollectionManager") as mock_product_manager_class:
                    service = DropshipProductFinderService(
                        db=mock_database_manager,
                        broker=mock_message_broker,
                        data_root="/tmp/test",
                        redis_client=None,
                    )

                    # Verify MockEbayCollector is used when USE_MOCK_FINDERS is True
                    assert isinstance(service.collectors["ebay"], MockEbayCollector)
                    assert isinstance(service.collectors["amazon"], AmazonProductCollector)

    @pytest.mark.asyncio
    async def test_init_without_mock_finders(self, mock_database_manager, mock_message_broker):
        """Test initialization with USE_MOCK_FINDERS=False"""
        mock_config = Mock()
        mock_config.USE_MOCK_FINDERS = False

        with patch("services.service.config", mock_config):
            with patch("services.service.ImageStorageManager") as mock_image_manager_class:
                with patch("services.service.ProductCollectionManager") as mock_product_manager_class:
                    service = DropshipProductFinderService(
                        db=mock_database_manager,
                        broker=mock_message_broker,
                        data_root="/tmp/test",
                        redis_client=None,
                    )

                    # Verify EbayProductCollector is used when USE_MOCK_FINDERS is False
                    assert isinstance(service.collectors["ebay"], EbayProductCollector)
                    assert isinstance(service.collectors["amazon"], AmazonProductCollector)

    @pytest.mark.asyncio
    async def test_handle_products_collect_request_with_images(
        self, dropship_service, mock_database_manager, mock_message_broker
    ):
        """Test handle_products_collect_request when images are found"""
        event_data = {
            "job_id": "test-job-123",
            "queries": {"en": ["laptop", "phone"]},
            "top_amz": 5,
            "top_ebay": 5,
        }

        await dropship_service.handle_products_collect_request(event_data)

        # Verify product collection was called
        dropship_service.product_collection_manager.collect_and_store_products.assert_called_once_with(
            "test-job-123", ["laptop", "phone"], 5, 5
        )

        # Verify image count was fetched
        mock_database_manager.fetch_val.assert_called_once()

        # Verify events were published
        assert mock_message_broker.publish_event.call_count == 2  # 2 from _publish_all_image_events

    @pytest.mark.asyncio
    async def test_handle_products_collect_request_with_zero_images(
        self, dropship_service, mock_database_manager, mock_message_broker
    ):
        """Test handle_products_collect_request when no images are found"""
        # Mock database to return 0 images
        mock_database_manager.fetch_val.return_value = 0

        event_data = {
            "job_id": "test-job-123",
            "queries": {"en": ["laptop", "phone"]},
            "top_amz": 5,
            "top_ebay": 5,
        }

        await dropship_service.handle_products_collect_request(event_data)

        # Verify product collection was called
        dropship_service.product_collection_manager.collect_and_store_products.assert_called_once_with(
            "test-job-123", ["laptop", "phone"], 5, 5
        )

        # Verify zero products case was handled
        assert mock_message_broker.publish_event.call_count == 2

        # Verify image storage manager was not called
        dropship_service.image_storage_manager.publish_individual_image_events.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_zero_products_case(
        self, dropship_service, mock_message_broker
    ):
        """Test _handle_zero_products_case method"""
        job_id = "test-job-123"

        await dropship_service._handle_zero_products_case(job_id)

        # Verify two events were published
        assert mock_message_broker.publish_event.call_count == 2

        # Verify products.collections.completed event
        collections_call = mock_message_broker.publish_event.call_args_list[0]
        assert collections_call[0][0] == "products.collections.completed"
        assert collections_call[1]["correlation_id"] == job_id

        # Verify the event data structure is correct
        collections_event_data = collections_call[0][1]
        assert "event_id" in collections_event_data
        assert collections_event_data["job_id"] == job_id

        # Verify products.images.ready.batch event
        images_call = mock_message_broker.publish_event.call_args_list[1]
        assert images_call[0][0] == "products.images.ready.batch"
        assert images_call[1]["correlation_id"] == job_id

        # Verify the event data structure is correct
        images_event_data = images_call[0][1]
        assert "event_id" in images_event_data
        assert images_event_data["job_id"] == job_id
        assert images_event_data["total_images"] == 0

    @pytest.mark.asyncio
    async def test_publish_all_image_events(
        self, dropship_service, mock_message_broker
    ):
        """Test _publish_all_image_events method"""
        job_id = "test-job-123"
        total_images = 5

        await dropship_service._publish_all_image_events(job_id, total_images)

        # Verify two events were published (2 from this method)
        assert mock_message_broker.publish_event.call_count == 2

        # Verify products.collections.completed event
        collections_call = mock_message_broker.publish_event.call_args_list[0]
        assert collections_call[0][0] == "products.collections.completed"
        assert collections_call[1]["correlation_id"] == job_id

        # Verify the event data structure is correct
        collections_event_data = collections_call[0][1]
        assert "event_id" in collections_event_data
        assert collections_event_data["job_id"] == job_id

        # Verify products.images.ready.batch event
        images_call = mock_message_broker.publish_event.call_args_list[1]
        assert images_call[0][0] == "products.images.ready.batch"
        assert images_call[1]["correlation_id"] == job_id

        # Verify the event data structure is correct
        images_event_data = images_call[0][1]
        assert "event_id" in images_event_data
        assert images_event_data["job_id"] == job_id
        assert images_event_data["total_images"] == total_images

        # Verify image storage manager was called
        dropship_service.image_storage_manager.publish_individual_image_events.assert_called_once_with(job_id)

    @pytest.mark.asyncio
    async def test_handle_products_collect_request_error_handling(
        self, dropship_service, mock_database_manager, mock_message_broker
    ):
        """Test error handling in handle_products_collect_request"""
        # Mock product collection manager to raise an exception
        dropship_service.product_collection_manager.collect_and_store_products.side_effect = Exception("Collection failed")

        event_data = {
            "job_id": "test-job-123",
            "queries": {"en": ["laptop", "phone"]},
            "top_amz": 5,
            "top_ebay": 5,
        }

        # Should raise the exception
        with pytest.raises(Exception, match="Collection failed"):
            await dropship_service.handle_products_collect_request(event_data)

        # Verify that the error was logged (we can't directly check logging, but we can verify the exception was raised)

    @pytest.mark.asyncio
    async def test_update_redis_client_with_mock_finders(
        self, dropship_service, mock_config
    ):
        """Test update_redis_client method with USE_MOCK_FINDERS=True"""
        mock_config.USE_MOCK_FINDERS = True
        mock_redis_client = Mock()

        # Add the missing method to the mock collector
        dropship_service.collectors["ebay"].update_redis_client = Mock()

        with patch("services.service.config", mock_config):
            dropship_service.update_redis_client(mock_redis_client)

            # Verify Redis client was updated
            assert dropship_service.redis == mock_redis_client

            # Verify eBay collector was NOT updated (since we're using mock)
            dropship_service.collectors["ebay"].update_redis_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_redis_client_without_mock_finders(
        self, dropship_service, mock_config
    ):
        """Test update_redis_client method with USE_MOCK_FINDERS=False"""
        mock_config.USE_MOCK_FINDERS = False
        mock_redis_client = Mock()

        # Add the missing method to the mock collector
        dropship_service.collectors["ebay"].update_redis_client = Mock()

        with patch("services.service.config", mock_config):
            dropship_service.update_redis_client(mock_redis_client)

            # Verify Redis client was updated
            assert dropship_service.redis == mock_redis_client

            # Verify eBay collector WAS updated (since we're using real collector)
            dropship_service.collectors["ebay"].update_redis_client.assert_called_once_with(mock_redis_client)

    @pytest.mark.asyncio
    async def test_close_method(self, dropship_service):
        """Test close method"""
        # Mock the collectors' close methods
        dropship_service.collectors["amazon"].close = AsyncMock()
        dropship_service.collectors["ebay"].close = AsyncMock()

        await dropship_service.close()

        # Verify all collectors were closed
        dropship_service.collectors["amazon"].close.assert_called_once()
        dropship_service.collectors["ebay"].close.assert_called_once()
