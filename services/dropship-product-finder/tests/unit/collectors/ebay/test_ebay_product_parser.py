import pytest
from collectors.ebay.ebay_product_parser import EbayProductParser

pytestmark = pytest.mark.unit


@pytest.fixture
def ebay_product_parser():
    """Fixture to provide an EbayProductParser instance."""
    return EbayProductParser()


def test_parse_search_results_with_details_success(ebay_product_parser):
    """
    Tests successful parsing when both summaries and detailed items are provided.
    Detailed items should take precedence.
    """
    summaries = [
        {"itemId": "1", "title": "Summary Item 1"},
        {"itemId": "2", "title": "Summary Item 2"},
        {"itemId": "3", "title": "Summary Item 3"},
    ]
    item_details = [
        {"item": {"itemId": "1", "title": "Detailed Item 1", "price": "10.00"}},
        {"item": {"itemId": "2", "title": "Detailed Item 2", "price": "20.00"}},
        # Simulate a case where item_details might be missing or different
        {"item": {"itemId": "3", "title": "Detailed Item 3", "price": "30.00"}},
    ]

    expected_parsed_items = [
        {"itemId": "1", "title": "Detailed Item 1", "price": "10.00"},
        {"itemId": "2", "title": "Detailed Item 2", "price": "20.00"},
        {"itemId": "3", "title": "Detailed Item 3", "price": "30.00"},
    ]

    parsed_items = ebay_product_parser.parse_search_results_with_details(summaries, item_details)
    assert parsed_items == expected_parsed_items


def test_parse_search_results_with_details_fallback_to_summary(ebay_product_parser):
    """
    Tests parsing when a detailed item is missing or malformed, falling back to summary.
    """
    summaries = [
        {"itemId": "1", "title": "Summary Item 1"},
        {"itemId": "2", "title": "Summary Item 2"},
    ]
    item_details = [
        {"item": {"itemId": "1", "title": "Detailed Item 1", "price": "10.00"}},
        {"some_other_key": "value"}  # Malformed detailed item, should fall back to summary
    ]

    expected_parsed_items = [
        {"itemId": "1", "title": "Detailed Item 1", "price": "10.00"},
        {"itemId": "2", "title": "Summary Item 2"},
    ]

    parsed_items = ebay_product_parser.parse_search_results_with_details(summaries, item_details)
    assert parsed_items == expected_parsed_items


def test_parse_search_results_with_details_uses_direct_payload(ebay_product_parser):
    """Detailed payloads without an "item" key should still take precedence."""
    summaries = [
        {"itemId": "1", "title": "Summary Item 1"},
    ]
    item_details = [
        {"itemId": "1", "title": "Detailed Item 1", "price": "10.00"},
    ]

    parsed_items = ebay_product_parser.parse_search_results_with_details(
        summaries, item_details
    )

    assert parsed_items == item_details


@pytest.mark.unit
def test_parse_search_results_with_details_empty_inputs(ebay_product_parser):
    """
    Tests parsing with empty summaries and item_details.
    """
    summaries = []
    item_details = []
    expected_parsed_items = []

    parsed_items = ebay_product_parser.parse_search_results_with_details(summaries, item_details)
    assert parsed_items == expected_parsed_items


@pytest.mark.unit
def test_parse_search_results_with_details_more_summaries_than_details(ebay_product_parser):
    """
    Tests parsing when there are more summaries than detailed items.
    Remaining summaries should be used.
    """
    summaries = [
        {"itemId": "1", "title": "Summary Item 1"},
        {"itemId": "2", "title": "Summary Item 2"},
        {"itemId": "3", "title": "Summary Item 3"},
    ]
    item_details = [
        {"item": {"itemId": "1", "title": "Detailed Item 1", "price": "10.00"}},
    ]

    expected_parsed_items = [
        {"itemId": "1", "title": "Detailed Item 1", "price": "10.00"},
        {"itemId": "2", "title": "Summary Item 2"},
        {"itemId": "3", "title": "Summary Item 3"},
    ]

    parsed_items = ebay_product_parser.parse_search_results_with_details(summaries, item_details)
    assert parsed_items == expected_parsed_items


@pytest.mark.unit
def test_parse_search_results_simple_pass_through(ebay_product_parser):
    """
    Tests the parse_search_results method, which is a simple pass-through.
    """
    items = [
        {"itemId": "1", "title": "Item 1"},
        {"itemId": "2", "title": "Item 2"},
    ]
    expected_items = [
        {"itemId": "1", "title": "Item 1"},
        {"itemId": "2", "title": "Item 2"},
    ]
    parsed_items = ebay_product_parser.parse_search_results(items)
    assert parsed_items == expected_items


@pytest.mark.unit
def test_parse_search_results_empty_list(ebay_product_parser):
    """
    Tests the parse_search_results method with an empty list.
    """
    items = []
    expected_items = []
    parsed_items = ebay_product_parser.parse_search_results(items)
    assert parsed_items == expected_items
