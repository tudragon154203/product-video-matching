import pytest
from collectors.ebay.ebay_product_mapper import EbayProductMapper

pytestmark = pytest.mark.unit


@pytest.fixture
def ebay_product_mapper():
    """Fixture to provide an EbayProductMapper instance."""
    return EbayProductMapper()


def test_normalize_ebay_item_full_details(ebay_product_mapper):
    """
    Tests successful normalization of an eBay item with full details,
    including primary and additional images, and shipping cost.
    """
    item = {
        "itemId": "123",
        "epid": "EPID123",
        "title": "Test Product",
        "brand": "TestBrand",
        "manufacturer": "TestManufacturer",
        "itemWebUrl": "http://example.com/item123",
        "itemAffiliateWebUrl": "http://affiliate.example.com/item123",
        "image": {"imageUrl": "http://example.com/image1.jpg"},
        "galleryInfo": {
            "imageVariations": [
                {"imageUrl": "http://example.com/gallery1.jpg"},
                {"imageUrl": "http://example.com/gallery2.jpg"},
                {"imageUrl": "http://example.com/gallery3.jpg"},
            ]
        },
        "images": [  # This is a less common structure but good to test
            {"imageUrl": "http://example.com/img_array_1.jpg"},
            {"imageUrl": "http://example.com/img_array_2.jpg"},
        ],
        "price": {"value": "100.00", "currency": "USD"},
        "shippingOptions": [
            {"shippingType": "STANDARD", "shippingCost": {"value": "10.00", "currency": "USD"}}
        ],
    }
    marketplace = "EBAY_US"

    expected_product = {
        "id": "EPID123",
        "title": "Test Product",
        "brand": "TestBrand",
        "url": "http://example.com/item123",
        "images": [
            "http://example.com/image1.jpg",
            "http://example.com/gallery2.jpg",
            "http://example.com/gallery3.jpg",
        ],
        "marketplace": "us",
        "price": 100.00,
        "currency": "USD",
        "epid": "EPID123",
        "itemId": "123",
        "totalPrice": 110.00,
        "shippingCost": 10.00,
    }

    normalized_product = ebay_product_mapper.normalize_ebay_item(item, marketplace)
    assert normalized_product == expected_product


def test_normalize_ebay_item_no_epid_fallback_to_item_id(ebay_product_mapper):
    """
    Tests normalization when EPID is missing, ensuring fallback to itemId for 'id'.
    """
    item = {
        "itemId": "456",
        "title": "Another Product",
        "price": {"value": "50.00", "currency": "USD"},
        "shippingOptions": [
            {"shippingType": "FREE", "shippingCost": {"value": "0.00", "currency": "USD"}}
        ],
    }
    marketplace = "EBAY_DE"

    expected_product = {
        "id": "456",
        "title": "Another Product",
        "brand": None,
        "url": None,
        "images": [],
        "marketplace": "de",
        "price": 50.00,
        "currency": "USD",
        "epid": None,
        "itemId": "456",
        "totalPrice": 50.00,
        "shippingCost": 0.00,
    }

    normalized_product = ebay_product_mapper.normalize_ebay_item(item, marketplace)
    assert normalized_product == expected_product


def test_normalize_ebay_item_free_shipping(ebay_product_mapper):
    """
    Tests normalization with free shipping.
    """
    item = {
        "itemId": "789",
        "title": "Free Shipping Item",
        "price": {"value": "25.00", "currency": "GBP"},
        "shippingOptions": [
            {"shippingType": "FREE", "shippingCost": {"value": "0.00", "currency": "GBP"}}
        ],
    }
    marketplace = "EBAY_UK"

    expected_product = {
        "id": "789",
        "title": "Free Shipping Item",
        "brand": None,
        "url": None,
        "images": [],
        "marketplace": "uk",
        "price": 25.00,
        "currency": "GBP",
        "epid": None,
        "itemId": "789",
        "totalPrice": 25.00,
        "shippingCost": 0.00,
    }

    normalized_product = ebay_product_mapper.normalize_ebay_item(item, marketplace)
    assert normalized_product == expected_product


def test_normalize_ebay_item_image_precedence(ebay_product_mapper):
    """
    Tests that primary image is extracted in the correct order of precedence:
    1. item["image"]["imageUrl"] (if detailed)
    2. item["galleryInfo"]["imageVariations"][0]["imageUrl"]
    3. item["image"]["imageUrl"] (if from summary)
    """
    # Case 1: Image from item["image"] in detailed response
    item1 = {
        "itemId": "1",
        "title": "Product 1",
        "image": {"imageUrl": "image_from_detailed_item.jpg"},
        "galleryInfo": {"imageVariations": [{"imageUrl": "image_from_gallery.jpg"}]},
        "price": {"value": "10", "currency": "USD"},
        "shippingOptions": [{"shippingCost": {"value": "0"}}],
    }
    product1 = ebay_product_mapper.normalize_ebay_item(item1, "EBAY_US")
    assert product1["images"][0] == "image_from_detailed_item.jpg"

    # Case 2: Image from galleryInfo if item["image"] is not available or malformed
    item2 = {
        "itemId": "2",
        "title": "Product 2",
        "galleryInfo": {"imageVariations": [{"imageUrl": "image_from_gallery.jpg"}]},
        "price": {"value": "10", "currency": "USD"},
        "shippingOptions": [{"shippingCost": {"value": "0"}}],
    }
    product2 = ebay_product_mapper.normalize_ebay_item(item2, "EBAY_US")
    assert product2["images"][0] == "image_from_gallery.jpg"

    # Case 3: Image from item["image"] in summary response if no detailed or gallery info
    item3 = {
        "itemId": "3",
        "title": "Product 3",
        "image": {"imageUrl": "image_from_summary.jpg"},
        "price": {"value": "10", "currency": "USD"},
        "shippingOptions": [{"shippingCost": {"value": "0"}}],
    }
    product3 = ebay_product_mapper.normalize_ebay_item(item3, "EBAY_US")
    assert product3["images"][0] == "image_from_summary.jpg"


@pytest.mark.unit
def test_normalize_ebay_item_additional_images_limit(ebay_product_mapper):
    """
    Tests that additional images are limited to 5 and correctly sourced.
    """
    item = {
        "itemId": "1",
        "title": "Product with many images",
        "image": {"imageUrl": "primary.jpg"},
        "galleryInfo": {
            "imageVariations": [
                {"imageUrl": "gallery1.jpg"},
                {"imageUrl": "gallery2.jpg"},
                {"imageUrl": "gallery3.jpg"},
                {"imageUrl": "gallery4.jpg"},
                {"imageUrl": "gallery5.jpg"},
                {"imageUrl": "gallery6.jpg"},
                {"imageUrl": "gallery7.jpg"},
            ]
        },
        "images": [
            {"imageUrl": "img_array1.jpg"},
            {"imageUrl": "img_array2.jpg"},
            {"imageUrl": "img_array3.jpg"},
            {"imageUrl": "img_array4.jpg"},
            {"imageUrl": "img_array5.jpg"},
        ],
        "price": {"value": "10", "currency": "USD"},
        "shippingOptions": [{"shippingCost": {"value": "0"}}],
    }
    marketplace = "EBAY_US"

    normalized_product = ebay_product_mapper.normalize_ebay_item(item, marketplace)
    # Primary image + 5 additional images
    assert len(normalized_product["images"]) == 6
    assert normalized_product["images"] == [
        "primary.jpg",
        "gallery2.jpg",  # gallery1.jpg is skipped as it's the first in imageVariations (effectively primary)
        "gallery3.jpg",
        "gallery4.jpg",
        "gallery5.jpg",
        "gallery6.jpg",
    ]


@pytest.mark.unit
def test_normalize_ebay_item_missing_required_fields(ebay_product_mapper):
    """
    Tests that normalize_ebay_item returns None if a critical field like 'itemId' is missing.
    """
    item = {
        "title": "Invalid Product",
        "price": {"value": "10.00", "currency": "USD"},
    }
    marketplace = "EBAY_US"
    normalized_product = ebay_product_mapper.normalize_ebay_item(item, marketplace)
    assert normalized_product is None


@pytest.mark.unit
def test_deduplicate_products_by_item_id(ebay_product_mapper):
    """
    Tests deduplication by itemId, selecting the product with the lowest total price.
    """
    products = [
        {"id": "A", "itemId": "A", "totalPrice": 100.00},
        {"id": "B", "itemId": "B", "totalPrice": 150.00},
        {"id": "A", "itemId": "A", "totalPrice": 90.00},  # Lower price for itemId A
        {"id": "C", "itemId": "C", "totalPrice": 120.00},
    ]
    max_items = 3

    deduplicated = ebay_product_mapper.deduplicate_products(products, max_items)
    assert len(deduplicated) == 3
    assert deduplicated[0]["id"] == "A"  # Lowest total price for itemId A
    assert deduplicated[0]["totalPrice"] == 90.00
    assert deduplicated[1]["id"] == "C"
    assert deduplicated[1]["totalPrice"] == 120.00
    assert deduplicated[2]["id"] == "B"
    assert deduplicated[2]["totalPrice"] == 150.00


@pytest.mark.unit
def test_deduplicate_products_empty_list(ebay_product_mapper):
    """
    Tests deduplication with an empty list of products.
    """
    products = []
    max_items = 5
    deduplicated = ebay_product_mapper.deduplicate_products(products, max_items)
    assert deduplicated == []


@pytest.mark.unit
def test_deduplicate_products_max_items_limit(ebay_product_mapper):
    """
    Tests that the max_items limit is correctly applied after deduplication and sorting.
    """
    products = [
        {"id": "A", "itemId": "A", "totalPrice": 100.00},
        {"id": "B", "itemId": "B", "totalPrice": 150.00},
        {"id": "A", "itemId": "A", "totalPrice": 90.00},
        {"id": "C", "itemId": "C", "totalPrice": 120.00},
        {"id": "D", "itemId": "D", "totalPrice": 80.00},
    ]
    max_items = 2

    deduplicated = ebay_product_mapper.deduplicate_products(products, max_items)
    assert len(deduplicated) == 2
    assert deduplicated[0]["totalPrice"] == 80.00  # itemId D
    assert deduplicated[1]["totalPrice"] == 90.00  # itemId A


@pytest.mark.unit
def test_deduplicate_products_with_variant_item_ids(ebay_product_mapper):
    """
    Tests deduplication when itemId has variant format like 'v1|364926706252|634516979679',
    keeping only one variant per product ID.
    """
    products = [
        {
            "id": "v1|364926706252|634516979679",
            "itemId": "v1|364926706252|634516979679",
            "totalPrice": 100.00
        },
        {
            "id": "v1|364926706252|634516979680",
            "itemId": "v1|364926706252|634516979680",
            "totalPrice": 95.00  # Lower price for same product
        },
        {
            "id": "v1|123456789|987654321",
            "itemId": "v1|123456789|987654321",
            "totalPrice": 120.00
        },
        {
            "id": "v1|123456789|987654322",
            "itemId": "v1|123456789|987654322",
            "totalPrice": 110.00  # Lower price for same product
        },
        {
            "id": "simple_item_id",
            "itemId": "simple_item_id",
            "totalPrice": 80.00
        }
    ]
    max_items = 5

    deduplicated = ebay_product_mapper.deduplicate_products(products, max_items)
    assert len(deduplicated) == 3  # One variant per product ID

    # Should keep the lowest priced variant for each product
    product_ids = [p["id"] for p in deduplicated]
    assert "v1|364926706252|634516979680" in product_ids  # Lower price variant
    assert "v1|123456789|987654322" in product_ids  # Lower price variant
    assert "simple_item_id" in product_ids

    # Sorted by total price
    assert deduplicated[0]["totalPrice"] == 80.00  # simple_item_id
    assert deduplicated[1]["totalPrice"] == 95.00  # product 364926706252 variant
    assert deduplicated[2]["totalPrice"] == 110.00  # product 123456789 variant


@pytest.mark.unit
def test_extract_product_id_from_variant(ebay_product_mapper):
    """
    Tests the _extract_product_id_from_variant helper method.
    """
    # Valid variant format
    assert ebay_product_mapper._extract_product_id_from_variant("v1|364926706252|634516979679") == "364926706252"
    assert ebay_product_mapper._extract_product_id_from_variant("v2|123456789|987654321") == "123456789"

    # Invalid formats
    assert ebay_product_mapper._extract_product_id_from_variant("simple_id") is None
    assert ebay_product_mapper._extract_product_id_from_variant("364926706252|634516979679") is None  # Missing version
    assert ebay_product_mapper._extract_product_id_from_variant("v1|364926706252") is None  # Missing variant ID
    assert ebay_product_mapper._extract_product_id_from_variant("") is None
    assert ebay_product_mapper._extract_product_id_from_variant(None) is None
    assert ebay_product_mapper._extract_product_id_from_variant(123) is None
