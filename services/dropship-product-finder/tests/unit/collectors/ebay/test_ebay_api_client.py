from services.ebay_browse_api_client import EbayBrowseApiClient
from collectors.ebay.ebay_api_client import EbayApiClient
import pytest
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_ebay_browse_api_client():
    """Fixture to provide a mock EbayBrowseApiClient."""
    return AsyncMock(spec=EbayBrowseApiClient)


@pytest.fixture
def ebay_api_client(mock_ebay_browse_api_client):
    """Fixture to provide an EbayApiClient instance with a mocked browse client."""
    return EbayApiClient(browse_client=mock_ebay_browse_api_client)


@pytest.mark.asyncio
async def test_fetch_and_get_details_success(ebay_api_client, mock_ebay_browse_api_client):
    """
    Tests successful fetching of search results and item details.
    """
    # Mock search results and item details
    mock_search_results = {
        "itemSummaries": [
            {"itemId": "1", "title": "Item 1 Summary"},
            {"itemId": "2", "title": "Item 2 Summary"},
        ]
    }
    mock_detailed_item_1 = {"item": {"itemId": "1", "title": "Item 1 Detail"}}
    mock_detailed_item_2 = {"item": {"itemId": "2", "title": "Item 2 Detail"}}

    mock_ebay_browse_api_client.search.return_value = mock_search_results
    mock_ebay_browse_api_client.get_item.side_effect = [mock_detailed_item_1, mock_detailed_item_2]

    query = "test query"
    limit = 10
    offset = 0
    marketplace = "EBAY_US"
    top_k = 2

    summaries, details = await ebay_api_client.fetch_and_get_details(
        query, limit, offset, marketplace, top_k
    )

    mock_ebay_browse_api_client.search.assert_called_once_with(q=query, limit=limit, offset=offset)
    assert mock_ebay_browse_api_client.get_item.call_count == top_k
    assert summaries == mock_search_results["itemSummaries"]
    assert details == [mock_detailed_item_1, mock_detailed_item_2]


@pytest.mark.asyncio
async def test_fetch_and_get_details_with_get_item_failure(
    ebay_api_client, mock_ebay_browse_api_client, monkeypatch
):
    """
    Tests fetching with a failure in get_item, ensuring fallback to summary.
    """
    mock_search_results = {
        "itemSummaries": [
            {"itemId": "1", "title": "Item 1 Summary"},
            {"itemId": "2", "title": "Item 2 Summary"},
        ]
    }
    mock_detailed_item_1 = {"item": {"itemId": "1", "title": "Item 1 Detail"}}

    mock_ebay_browse_api_client.search.return_value = mock_search_results
    mock_ebay_browse_api_client.get_item.side_effect = [
        mock_detailed_item_1,
        Exception("Failed to get item details"),
    ]

    query = "test query"
    limit = 10
    offset = 0
    marketplace = "EBAY_US"
    top_k = 2

    mock_logger = MagicMock()
    monkeypatch.setattr("collectors.ebay.ebay_api_client.logger", mock_logger)

    summaries, details = await ebay_api_client.fetch_and_get_details(
        query, limit, offset, marketplace, top_k
    )

    mock_ebay_browse_api_client.search.assert_called_once_with(q=query, limit=limit, offset=offset)
    assert mock_ebay_browse_api_client.get_item.call_count == top_k
    assert summaries == mock_search_results["itemSummaries"]
    assert details == [mock_detailed_item_1, {"item": mock_search_results["itemSummaries"][1]}]
    mock_logger.warning.assert_called_once()
    warning_args, warning_kwargs = mock_logger.warning.call_args
    assert warning_args[0].startswith("Failed to get details for item 2")


@pytest.mark.asyncio
async def test_fetch_and_get_details_empty_search_results(ebay_api_client, mock_ebay_browse_api_client):
    """
    Tests behavior when search results are empty.
    """
    mock_search_results = {"itemSummaries": []}
    mock_ebay_browse_api_client.search.return_value = mock_search_results

    query = "no results"
    limit = 10
    offset = 0
    marketplace = "EBAY_US"
    top_k = 2

    summaries, details = await ebay_api_client.fetch_and_get_details(
        query, limit, offset, marketplace, top_k
    )

    mock_ebay_browse_api_client.search.assert_called_once_with(q=query, limit=limit, offset=offset)
    mock_ebay_browse_api_client.get_item.assert_not_called()
    assert summaries == []
    assert details == []


@pytest.mark.asyncio
async def test_fetch_and_get_details_top_k_limit(ebay_api_client, mock_ebay_browse_api_client):
    """
    Tests that top_k correctly limits the number of detailed items fetched.
    """
    mock_search_results = {
        "itemSummaries": [
            {"itemId": "1", "title": "Item 1 Summary"},
            {"itemId": "2", "title": "Item 2 Summary"},
            {"itemId": "3", "title": "Item 3 Summary"},
        ]
    }
    mock_detailed_item_1 = {"item": {"itemId": "1", "title": "Item 1 Detail"}}
    mock_detailed_item_2 = {"item": {"itemId": "2", "title": "Item 2 Detail"}}

    mock_ebay_browse_api_client.search.return_value = mock_search_results
    mock_ebay_browse_api_client.get_item.side_effect = [mock_detailed_item_1, mock_detailed_item_2]

    query = "test query"
    limit = 10
    offset = 0
    marketplace = "EBAY_US"
    top_k = 2

    summaries, details = await ebay_api_client.fetch_and_get_details(
        query, limit, offset, marketplace, top_k
    )

    mock_ebay_browse_api_client.search.assert_called_once_with(q=query, limit=limit, offset=offset)
    assert mock_ebay_browse_api_client.get_item.call_count == top_k
    assert summaries == mock_search_results["itemSummaries"]
    assert details == [mock_detailed_item_1, mock_detailed_item_2]
