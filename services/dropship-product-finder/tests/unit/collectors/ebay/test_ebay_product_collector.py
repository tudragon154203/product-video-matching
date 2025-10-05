from types import SimpleNamespace
from services.auth import eBayAuthService
from collectors.ebay.ebay_api_client import EbayApiClient
from collectors.ebay.ebay_product_collector import EbayProductCollector
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_config():
    """Mock configuration object."""
    return SimpleNamespace(
        EBAY_MARKETPLACES="EBAY_US,EBAY_DE",
        EBAY_BROWSE_BASE="http://mock-ebay-browse.com",
    )


@pytest.fixture
def mock_auth_service():
    """Mock eBayAuthService."""
    return MagicMock(spec=eBayAuthService)


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient."""
    return AsyncMock()


@pytest.fixture
def mock_redis_client():
    """Mock redis client."""
    return MagicMock()


@pytest.fixture
def ebay_product_collector(
    mock_config,
    mock_auth_service,
    mock_httpx_client,
    mock_redis_client,
):
    """Fixture for EbayProductCollector with mocked dependencies."""
    original_auth_service = globals().get("eBayAuthService")

    with patch(
        "collectors.ebay.ebay_product_collector.EbayBrowseApiClient"
    ) as MockEbayBrowseApiClient, patch(
        "collectors.ebay.ebay_product_collector.EbayProductMapper"
    ) as MockEbayProductMapper, patch(
        "collectors.ebay.ebay_product_collector.EbayProductParser"
    ) as MockEbayProductParser, patch(
        "collectors.ebay.ebay_product_collector.EbayApiClient"
    ) as MockEbayApiClient, patch(
        "collectors.ebay.ebay_product_collector.config",
        mock_config,
    ), patch(
        "collectors.ebay.ebay_product_collector.eBayAuthService"
    ) as MockEbayAuthService:
        MockEbayAuthService.return_value = mock_auth_service
        globals()["eBayAuthService"] = MockEbayAuthService

        collector = EbayProductCollector(
            data_root="/tmp",
            httpx_client=mock_httpx_client,
            redis_client=mock_redis_client,
        )

        collector.ebay_api_client_class = MockEbayApiClient
        collector.ebay_parser = MockEbayProductParser.return_value
        collector.ebay_mapper = MockEbayProductMapper.return_value

        yield collector

    if original_auth_service is not None:
        globals()["eBayAuthService"] = original_auth_service


@pytest.mark.asyncio
async def test_init_initializes_dependencies(ebay_product_collector, mock_config, mock_auth_service, mock_redis_client):
    """
    Tests that the collector's __init__ method correctly initializes its dependencies
    and browse clients for each marketplace.
    """
    assert ebay_product_collector.auth_service == mock_auth_service
    assert ebay_product_collector.marketplaces == ["EBAY_US", "EBAY_DE"]
    assert ebay_product_collector.base_url == mock_config.EBAY_BROWSE_BASE
    assert ebay_product_collector.httpx_client == mock_httpx_client

    # Check that browse clients were initialized
    assert "EBAY_US" in ebay_product_collector.browse_clients
    assert "EBAY_DE" in ebay_product_collector.browse_clients
    assert isinstance(ebay_product_collector.browse_clients["EBAY_US"], MagicMock)
    assert isinstance(ebay_product_collector.browse_clients["EBAY_DE"], MagicMock)

    # Check that eBayAuthService was called with the correct config and redis_client
    eBayAuthService.assert_called_once_with(mock_config, mock_redis_client)


def test_get_source_name(ebay_product_collector):
    """Tests that get_source_name returns 'ebay'."""
    assert ebay_product_collector.get_source_name() == "ebay"


def test_update_redis_client(ebay_product_collector, mock_auth_service):
    """Tests that update_redis_client updates the redis client in the auth service."""
    new_redis_client = MagicMock()
    ebay_product_collector.update_redis_client(new_redis_client)
    mock_auth_service.update_redis_client.assert_called_once_with(new_redis_client)


@pytest.mark.asyncio
async def test_collect_products_success(ebay_product_collector):
    """
    Tests successful product collection across multiple marketplaces,
    including API calls, parsing, mapping, and deduplication.
    """
    query = "test query"
    top_k = 2

    # Mock the behavior of EbayApiClient, EbayProductParser, and EbayProductMapper
    mock_api_client_us = MagicMock(spec=EbayApiClient)
    mock_api_client_de = MagicMock(spec=EbayApiClient)

    ebay_product_collector.ebay_api_client_class.side_effect = [mock_api_client_us, mock_api_client_de]

    mock_api_client_us.fetch_and_get_details.return_value = (
        [{"itemId": "1_us_sum"}, {"itemId": "2_us_sum"}],
        [{"item": {"itemId": "1_us_det", "price": {"value": "100"}, "shippingOptions": [{"shippingCost": {"value": "10"}}], "totalPrice": 110.0}},
         {"item": {"itemId": "2_us_det", "price": {"value": "150"}, "shippingOptions": [{"shippingCost": {"value": "5"}}], "totalPrice": 155.0}}]
    )
    mock_api_client_de.fetch_and_get_details.return_value = (
        [{"itemId": "1_de_sum"}, {"itemId": "2_de_sum"}],
        [{"item": {"itemId": "1_de_det", "price": {"value": "90"}, "shippingOptions": [{"shippingCost": {"value": "10"}}], "totalPrice": 100.0}},
         {"item": {"itemId": "2_de_det", "price": {"value": "120"}, "shippingOptions": [{"shippingCost": {"value": "5"}}], "totalPrice": 125.0}}]
    )

    ebay_product_collector.ebay_parser.parse_search_results_with_details.side_effect = [
        [{"itemId": "1_us_parsed", "price": {"value": "100"}}, {"itemId": "2_us_parsed", "price": {"value": "150"}}],
        [{"itemId": "1_de_parsed", "price": {"value": "90"}}, {"itemId": "2_de_parsed", "price": {"value": "120"}}]
    ]

    mock_product_us1 = {"id": "1", "itemId": "1_us", "totalPrice": 110.0}
    mock_product_us2 = {"id": "2", "itemId": "2_us", "totalPrice": 155.0}
    mock_product_de1 = {"id": "3", "itemId": "1_de", "totalPrice": 100.0}
    mock_product_de2 = {"id": "4", "itemId": "2_de", "totalPrice": 125.0}

    ebay_product_collector.ebay_mapper.normalize_ebay_item.side_effect = [
        mock_product_us1, mock_product_us2, mock_product_de1, mock_product_de2
    ]

    expected_deduplicated_products = [
        mock_product_de1,  # Lowest total price
        mock_product_us1,
    ]
    ebay_product_collector.ebay_mapper.deduplicate_products.return_value = expected_deduplicated_products

    products = await ebay_product_collector.collect_products(query, top_k)

    # Assertions
    assert products == expected_deduplicated_products
    assert ebay_product_collector.ebay_api_client_class.call_count == 2  # Called for each marketplace
    assert mock_api_client_us.fetch_and_get_details.await_count == 1
    assert mock_api_client_de.fetch_and_get_details.await_count == 1
    assert ebay_product_collector.ebay_parser.parse_search_results_with_details.call_count == 2
    assert ebay_product_collector.ebay_mapper.normalize_ebay_item.call_count == 4  # 2 for each marketplace
    ebay_product_collector.ebay_mapper.deduplicate_products.assert_called_once()


@pytest.mark.asyncio
async def test_collect_products_marketplace_error_resilience(ebay_product_collector):
    """
    Tests that the collector is resilient to errors in one marketplace
    and continues to collect from others.
    """
    query = "error test"
    top_k = 1

    mock_api_client_us = MagicMock(spec=EbayApiClient)
    mock_api_client_de = MagicMock(spec=EbayApiClient)

    ebay_product_collector.ebay_api_client_class.side_effect = [mock_api_client_us, mock_api_client_de]

    # Simulate an error for EBAY_US
    mock_api_client_us.fetch_and_get_details.side_effect = Exception("API Error for US")

    # EBAY_DE works fine
    mock_api_client_de.fetch_and_get_details.return_value = (
        [{"itemId": "1_de_sum"}],
        [{"item": {"itemId": "1_de_det", "price": {"value": "90"}, "shippingOptions": [{"shippingCost": {"value": "10"}}], "totalPrice": 100.0}}]
    )

    ebay_product_collector.ebay_parser.parse_search_results_with_details.return_value = [
        {"itemId": "1_de_parsed", "price": {"value": "90"}}
    ]
    mock_product_de1 = {"id": "3", "itemId": "1_de", "totalPrice": 100.0}
    ebay_product_collector.ebay_mapper.normalize_ebay_item.return_value = mock_product_de1
    ebay_product_collector.ebay_mapper.deduplicate_products.return_value = [mock_product_de1]

    products = await ebay_product_collector.collect_products(query, top_k)

    assert len(products) == 1
    assert products[0]["id"] == "3"
    assert mock_api_client_us.fetch_and_get_details.await_count == 1  # US was called
    assert mock_api_client_de.fetch_and_get_details.await_count == 1  # DE was called
    # Parser and mapper should only be called for the successful marketplace (DE)
    ebay_product_collector.ebay_parser.parse_search_results_with_details.assert_called_once()
    ebay_product_collector.ebay_mapper.normalize_ebay_item.assert_called_once()
    ebay_product_collector.ebay_mapper.deduplicate_products.assert_called_once()


@pytest.mark.asyncio
async def test_collect_products_no_results(ebay_product_collector):
    """
    Tests behavior when no products are found across all marketplaces.
    """
    query = "no products"
    top_k = 5

    mock_api_client_us = MagicMock(spec=EbayApiClient)
    mock_api_client_de = MagicMock(spec=EbayApiClient)
    ebay_product_collector.ebay_api_client_class.side_effect = [mock_api_client_us, mock_api_client_de]

    mock_api_client_us.fetch_and_get_details.return_value = ([], [])
    mock_api_client_de.fetch_and_get_details.return_value = ([], [])

    ebay_product_collector.ebay_parser.parse_search_results_with_details.return_value = []
    ebay_product_collector.ebay_mapper.normalize_ebay_item.return_value = None  # No products to normalize
    ebay_product_collector.ebay_mapper.deduplicate_products.return_value = []

    products = await ebay_product_collector.collect_products(query, top_k)

    assert products == []
    assert ebay_product_collector.ebay_api_client_class.call_count == 2
    assert mock_api_client_us.fetch_and_get_details.await_count == 1
    assert mock_api_client_de.fetch_and_get_details.await_count == 1
    assert ebay_product_collector.ebay_parser.parse_search_results_with_details.call_count == 2
    ebay_product_collector.ebay_mapper.normalize_ebay_item.assert_not_called()
    ebay_product_collector.ebay_mapper.deduplicate_products.assert_called_once_with([], top_k)


@pytest.mark.asyncio
async def test_collect_products_no_browse_client_for_marketplace(ebay_product_collector):
    """
    Tests handling of a marketplace for which no browse client was initialized.
    """
    # Temporarily remove one browse client to simulate this scenario
    del ebay_product_collector.browse_clients["EBAY_DE"]

    query = "partial success"
    top_k = 1

    mock_api_client_us = MagicMock(spec=EbayApiClient)
    ebay_product_collector.ebay_api_client_class.side_effect = [mock_api_client_us]  # Only for US

    mock_api_client_us.fetch_and_get_details.return_value = (
        [{"itemId": "1_us_sum"}],
        [{"item": {"itemId": "1_us_det", "price": {"value": "100"}, "shippingOptions": [{"shippingCost": {"value": "10"}}], "totalPrice": 110.0}}]
    )
    ebay_product_collector.ebay_parser.parse_search_results_with_details.return_value = [
        {"itemId": "1_us_parsed", "price": {"value": "100"}}
    ]
    mock_product_us1 = {"id": "1", "itemId": "1_us", "totalPrice": 110.0}
    ebay_product_collector.ebay_mapper.normalize_ebay_item.return_value = mock_product_us1
    ebay_product_collector.ebay_mapper.deduplicate_products.return_value = [mock_product_us1]

    products = await ebay_product_collector.collect_products(query, top_k)

    assert len(products) == 1
    assert products[0]["id"] == "1"
    assert mock_api_client_us.fetch_and_get_details.await_count == 1
    ebay_product_collector.ebay_parser.parse_search_results_with_details.assert_called_once()
    ebay_product_collector.ebay_mapper.normalize_ebay_item.assert_called_once()
    ebay_product_collector.ebay_mapper.deduplicate_products.assert_called_once()
