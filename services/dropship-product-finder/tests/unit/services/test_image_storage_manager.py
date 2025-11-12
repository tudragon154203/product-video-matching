import uuid
from common_py.models import ProductImage
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
    # Mock database connection and pool
    conn_execute_mock = MagicMock(execute=AsyncMock(), fetchval=AsyncMock())
    conn_mock = MagicMock(execute=AsyncMock(), __aenter__=AsyncMock(return_value=conn_execute_mock), __aexit__=AsyncMock())
    db_mock.pool.acquire = MagicMock(return_value=conn_mock)
    broker_mock = MagicMock(publish_event=AsyncMock())
    image_crud_mock = MagicMock(create_product_image=AsyncMock(), create_product_image_with_conn=AsyncMock())

    # Mock collector for download_image
    collector_mock = MagicMock()
    collector_mock.download_image = AsyncMock(side_effect=[LOCAL_PATH_0, LOCAL_PATH_1])

    collectors_mock = {SOURCE: collector_mock}

    # Patch ImageStorageManager dependencies
    with patch('services.image_storage_manager.ProductImageCRUD', return_value=image_crud_mock), \
            patch('services.image_storage_manager.ProductCRUD'):

        manager = ImageStorageManager(db=db_mock, broker=broker_mock, collectors=collectors_mock)
        yield manager, db_mock, broker_mock, image_crud_mock, collector_mock


@pytest.mark.asyncio
async def test_store_product_success(mock_dependencies):
    manager, db_mock, broker_mock, image_crud_mock, collector_mock = mock_dependencies

    with patch('uuid.uuid4', return_value=MagicMock(spec=uuid.UUID, hex=PRODUCT_ID, __str__=lambda self: PRODUCT_ID)), \
            patch('services.image_storage_manager.logger'):

        await manager.store_product(PRODUCT_DATA, JOB_ID, SOURCE, "test_correlation_id")

    # 1. Verify product was inserted
    assert db_mock.pool.acquire.called

    # 2. Verify images were downloaded
    assert collector_mock.download_image.call_count == 2

    # 3. Verify images were stored in database
    assert image_crud_mock.create_product_image_with_conn.call_count == 2

    # 4. Verify events were published
    assert broker_mock.publish_event.call_count == 2


@pytest.mark.asyncio
async def test_store_product_handles_download_failure(mock_dependencies):
    manager, db_mock, _, image_crud_mock, collector_mock = mock_dependencies

    # Simulate download failure for second image
    collector_mock.download_image.side_effect = [LOCAL_PATH_0, None]

    with patch('uuid.uuid4', return_value=MagicMock(spec=uuid.UUID, hex=PRODUCT_ID, __str__=lambda self: PRODUCT_ID)), \
            patch('services.image_storage_manager.logger'):

        await manager.store_product(PRODUCT_DATA, JOB_ID, SOURCE, "test_correlation_id")

    # 1. Verify Product INSERT still happened
    assert db_mock.pool.acquire.called

    # 2. Verify download attempts
    assert collector_mock.download_image.call_count == 2

    # 3. Verify ProductImage insert was only called once for successful download
    assert image_crud_mock.create_product_image_with_conn.call_count == 1
    # Check the call parameters - the mock includes both image and conn parameters
    actual_calls = image_crud_mock.create_product_image_with_conn.call_args_list
    assert len(actual_calls) == 1
    # Extract just the image parameter (first parameter) from the call
    actual_image_param = actual_calls[0][0][0]  # First call, first positional argument (image)
    assert actual_image_param.img_id == IMAGE_ID_0
    assert actual_image_param.product_id == PRODUCT_ID
    assert actual_image_param.local_path == LOCAL_PATH_0

    # 4. Verify no error was logged for a skipped image (local_path is None)


@pytest.mark.asyncio
async def test_store_product_handles_download_exception(mock_dependencies):
    manager, db_mock, _, image_crud_mock, collector_mock = mock_dependencies

    # Simulate download exception for second image
    collector_mock.download_image.side_effect = [LOCAL_PATH_0, Exception("Network timeout")]

    # Patch internal logger to check for error in _download_and_store_product_images
    with patch('uuid.uuid4', return_value=MagicMock(spec=uuid.UUID, hex=PRODUCT_ID, __str__=lambda self: PRODUCT_ID)), \
            patch('services.image_storage_manager.logger'):

        await manager.store_product(PRODUCT_DATA, JOB_ID, SOURCE, "test_correlation_id")

    # 1. Verify Product INSERT still happened
    assert db_mock.pool.acquire.called

    # 2. Verify download attempts
    assert collector_mock.download_image.call_count == 2

    # 3. Verify only one image was stored (successful download)
    assert image_crud_mock.create_product_image_with_conn.call_count == 1
    # Check the call parameters
    actual_calls = image_crud_mock.create_product_image_with_conn.call_args_list
    assert len(actual_calls) == 1
    actual_image_param = actual_calls[0][0][0]
    assert actual_image_param.img_id == IMAGE_ID_0
    assert actual_image_param.product_id == PRODUCT_ID
    assert actual_image_param.local_path == LOCAL_PATH_0


@pytest.mark.asyncio
async def test_store_product_publishes_events_immediately(mock_dependencies):
    manager, db_mock, broker_mock, image_crud_mock, collector_mock = mock_dependencies

    with patch('uuid.uuid4', return_value=MagicMock(spec=uuid.UUID, hex=PRODUCT_ID, __str__=lambda self: PRODUCT_ID)), \
            patch('services.image_storage_manager.logger'):

        await manager.store_product(PRODUCT_DATA, JOB_ID, SOURCE, "test_correlation_id")

    # 2. Verify events were published after successful transaction
    expected_topics = ["products.image.ready", "products.image.ready"]
    actual_topics = [call[0][0] for call in broker_mock.publish_event.call_args_list]
    assert actual_topics == expected_topics


@pytest.mark.asyncio
async def test_store_product_handles_event_publishing_failure(mock_dependencies):
    manager, db_mock, broker_mock, image_crud_mock, collector_mock = mock_dependencies

    # Simulate event publishing failure
    broker_mock.publish_event = AsyncMock(side_effect=[None, Exception("Publishing failed")])

    with patch('uuid.uuid4', return_value=MagicMock(spec=uuid.UUID, hex=PRODUCT_ID, __str__=lambda self: PRODUCT_ID)), \
            patch('services.image_storage_manager.logger'):

        await manager.store_product(PRODUCT_DATA, JOB_ID, SOURCE, "test_correlation_id")

    # 1. Verify product and images were still stored despite publishing failure
    assert db_mock.pool.acquire.called
    assert image_crud_mock.create_product_image_with_conn.call_count == 2


@pytest.mark.asyncio
async def test_store_product_handles_insertion_failure(mock_dependencies):
    manager, db_mock, _, image_crud_mock, collector_mock = mock_dependencies

    # Simulate database insertion failure
    image_crud_mock.create_product_image_with_conn = AsyncMock(side_effect=Exception("Database constraint"))

    with patch('uuid.uuid4', return_value=MagicMock(spec=uuid.UUID, hex=PRODUCT_ID, __str__=lambda self: PRODUCT_ID)), \
            patch('services.image_storage_manager.logger'):

        await manager.store_product(PRODUCT_DATA, JOB_ID, SOURCE, "test_correlation_id")

    # 1. Verify that download attempts were still made
    assert collector_mock.download_image.call_count == 2


@pytest.mark.asyncio
async def test_store_product_no_event_for_failed_download(mock_dependencies):
    manager, db_mock, broker_mock, image_crud_mock, collector_mock = mock_dependencies

    # Simulate complete download failure
    collector_mock.download_image.side_effect = [None, None]

    with patch('uuid.uuid4', return_value=MagicMock(spec=uuid.UUID, hex=PRODUCT_ID, __str__=lambda self: PRODUCT_ID)), \
            patch('services.image_storage_manager.logger'):

        await manager.store_product(PRODUCT_DATA, JOB_ID, SOURCE, "test_correlation_id")

    # 1. Verify product was inserted
    assert db_mock.pool.acquire.called

    # 2. Verify no events were published since no images were downloaded
    broker_mock.publish_event.assert_not_called()