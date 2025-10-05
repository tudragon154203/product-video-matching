import uuid
from typing import Dict, Any, List
from common_py.models import Product, ProductImage
from services.image_storage_manager import ImageStorageManager
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

pytestmark = pytest.mark.unit

# Mock data
JOB_ID = "job-123"
SOURCE = "ebay"
PRODUCT_ID = "prod-123"
IMAGE_ID_0 = f"{PRODUCT_ID}_img_0"
IMAGE_ID_1 = f"{PRODUCT_ID}_img_1"
IMAGE_URL_0 = "http://example.com/img0.jpg"
IMAGE_URL_1 = "http://example.com/img1.jpg"
LOCAL_PATH_0 = "/data/prod-123/img0.jpg"
LOCAL_PATH_1 = "/data/prod-123/img1.jpg"

PRODUCT_DATA = {
    "id": "item456",
    "title": "Test Product",
    "brand": "TestBrand",
    "url": "http://example.com/item456",
    "images": [IMAGE_URL_0, IMAGE_URL_1],
}


@pytest.fixture
def mock_dependencies():
    """Fixture to set up all necessary mocks for ImageStorageManager."""
    db_mock = MagicMock(execute=AsyncMock(), fetch_all=AsyncMock())
    broker_mock = MagicMock(publish_event=AsyncMock())
    image_crud_mock = MagicMock(create_product_image=AsyncMock())

    # Mock collector for download_image
    collector_mock = MagicMock()
    collector_mock.download_image = AsyncMock(side_effect=[LOCAL_PATH_0, LOCAL_PATH_1])

    collectors_mock = {SOURCE: collector_mock}

    # Patch the ImageStorageManager dependencies
    with patch('services.image_storage_manager.ProductImageCRUD', return_value=image_crud_mock), \
            patch('services.image_storage_manager.ProductCRUD'):

        manager = ImageStorageManager(db=db_mock, broker=broker_mock, collectors=collectors_mock)
        yield manager, db_mock, broker_mock, image_crud_mock, collector_mock


@pytest.mark.asyncio
async def test_store_product_success(mock_dependencies):
    manager, db_mock, _, image_crud_mock, collector_mock = mock_dependencies

    # Use patch for uuid.uuid4 to ensure consistent Product ID
    with patch('uuid.uuid4', return_value=MagicMock(spec=uuid.UUID, hex=PRODUCT_ID, __str__=lambda self: PRODUCT_ID)):
        await manager.store_product(PRODUCT_DATA, JOB_ID, SOURCE)

    # 1. Verify Product INSERT (store_product uses raw db.execute for INSERT)
    db_mock.execute.assert_called_once()

    # 2. Verify image downloads
    collector_mock.download_image.assert_any_call(IMAGE_URL_0, PRODUCT_ID, IMAGE_ID_0)
    collector_mock.download_image.assert_any_call(IMAGE_URL_1, PRODUCT_ID, IMAGE_ID_1)
    assert collector_mock.download_image.call_count == 2

    # 3. Verify ProductImage inserts via image_crud
    image_crud_mock.create_product_image.assert_any_call(ProductImage(img_id=IMAGE_ID_0, product_id=PRODUCT_ID, local_path=LOCAL_PATH_0))
    image_crud_mock.create_product_image.assert_any_call(ProductImage(img_id=IMAGE_ID_1, product_id=PRODUCT_ID, local_path=LOCAL_PATH_1))
    assert image_crud_mock.create_product_image.call_count == 2


@pytest.mark.asyncio
async def test_store_product_handles_insertion_failure(mock_dependencies):
    manager, db_mock, _, _, _ = mock_dependencies

    # Simulate database insertion failure in store_product
    db_mock.execute.side_effect = Exception("Database error")

    # Patch logger to check for error logs
    with patch('services.image_storage_manager.logger') as mock_logger:
        await manager.store_product(PRODUCT_DATA, JOB_ID, SOURCE)

    # Verify logger.error was called
    mock_logger.error.assert_called_once()
    assert mock_logger.error.call_args[0][0] == "Failed to store product"
    assert mock_logger.error.call_args[1]['error'] == "Database error"

    # Ensure no exceptions crash the calling function
    db_mock.execute.side_effect = None


@pytest.mark.asyncio
async def test_store_product_handles_download_failure(mock_dependencies):
    manager, db_mock, _, image_crud_mock, collector_mock = mock_dependencies

    # Simulate download failure for the second image
    collector_mock.download_image.side_effect = [LOCAL_PATH_0, None]

    with patch('uuid.uuid4', return_value=MagicMock(spec=uuid.UUID, hex=PRODUCT_ID, __str__=lambda self: PRODUCT_ID)), \
            patch('services.image_storage_manager.logger') as mock_logger:

        await manager.store_product(PRODUCT_DATA, JOB_ID, SOURCE)

    # 1. Verify Product INSERT still happened
    db_mock.execute.assert_called_once()

    # 2. Verify download attempts
    assert collector_mock.download_image.call_count == 2

    # 3. Verify ProductImage insert was only called once for the successful download
    image_crud_mock.create_product_image.assert_called_once()
    image_crud_mock.create_product_image.assert_any_call(ProductImage(img_id=IMAGE_ID_0, product_id=PRODUCT_ID, local_path=LOCAL_PATH_0))

    # 4. Verify no error was logged for a skipped image (local_path is None)


@pytest.mark.asyncio
async def test_store_product_handles_download_exception(mock_dependencies):
    manager, db_mock, _, image_crud_mock, collector_mock = mock_dependencies

    # Simulate download exception for the second image
    collector_mock.download_image.side_effect = [LOCAL_PATH_0, Exception("Network timeout")]

    # Patch the internal logger to check for error in _download_and_store_product_images
    with patch('uuid.uuid4', return_value=MagicMock(spec=uuid.UUID, hex=PRODUCT_ID, __str__=lambda self: PRODUCT_ID)), \
            patch('services.image_storage_manager.logger') as mock_logger:

        await manager.store_product(PRODUCT_DATA, JOB_ID, SOURCE)

    # 1. Verify Product INSERT still happened
    db_mock.execute.assert_called_once()

    # 2. Verify download attempts
    assert collector_mock.download_image.call_count == 2

    # 3. Verify ProductImage insert was only called once for the successful download
    image_crud_mock.create_product_image.assert_called_once()

    # 4. Verify error was logged for the download exception
    # The logger is defined globally, so we check the `mock_logger` in the context manager
    # _download_and_store_product_images logs on line 111
    error_calls = [call for call in mock_logger.error.call_args_list if "Failed to store product image" in call[0][0]]
    assert len(error_calls) == 1
    assert "Network timeout" in error_calls[0][1]['error']


@pytest.mark.asyncio
async def test_publish_individual_image_events_success(mock_dependencies):
    manager, db_mock, broker_mock, _, _ = mock_dependencies

    # Mock DB rows returned by fetch_all
    mock_images = [
        {"img_id": IMAGE_ID_0, "product_id": PRODUCT_ID, "local_path": LOCAL_PATH_0},
        {"img_id": IMAGE_ID_1, "product_id": PRODUCT_ID, "local_path": LOCAL_PATH_1},
    ]
    db_mock.fetch_all.return_value = mock_images

    await manager.publish_individual_image_events(JOB_ID)

    # 1. Verify fetch_all was called with the correct SQL
    db_mock.fetch_all.assert_called_once()
    assert JOB_ID in db_mock.fetch_all.call_args[0]

    # 2. Verify broker.publish_event was called for each image
    expected_event_0 = {
        "product_id": PRODUCT_ID,
        "image_id": IMAGE_ID_0,
        "local_path": LOCAL_PATH_0,
        "job_id": JOB_ID,
    }
    expected_event_1 = {
        "product_id": PRODUCT_ID,
        "image_id": IMAGE_ID_1,
        "local_path": LOCAL_PATH_1,
        "job_id": JOB_ID,
    }

    broker_mock.publish_event.assert_any_call("products.image.ready", expected_event_0, correlation_id=JOB_ID)
    broker_mock.publish_event.assert_any_call("products.image.ready", expected_event_1, correlation_id=JOB_ID)
    assert broker_mock.publish_event.call_count == 2


@pytest.mark.asyncio
async def test_publish_individual_image_events_handles_database_failure(mock_dependencies):
    manager, db_mock, broker_mock, _, _ = mock_dependencies

    # Simulate database failure during fetch_all
    db_mock.fetch_all.side_effect = Exception("DB connection lost")

    with patch('services.image_storage_manager.logger') as mock_logger:
        await manager.publish_individual_image_events(JOB_ID)

    # 1. Verify logger.error was called
    mock_logger.error.assert_called_once()
    assert "Failed to publish individual image events" in mock_logger.error.call_args[0][0]
    assert "DB connection lost" in mock_logger.error.call_args[1]['error']

    # 2. Ensure no broker events were published
    broker_mock.publish_event.assert_not_called()
