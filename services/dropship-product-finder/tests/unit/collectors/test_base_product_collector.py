from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock

from collectors.base_product_collector import BaseProductCollector

pytestmark = pytest.mark.unit


class DummyCollector(BaseProductCollector):
    async def collect_products(self, query: str, top_k: int):
        return []

    def get_source_name(self) -> str:
        return "dummy"


@pytest.mark.asyncio
async def test_download_image_without_pillow(monkeypatch, tmp_path):
    monkeypatch.setattr("collectors.base_product_collector.Image", None)
    mock_logger = MagicMock()
    monkeypatch.setattr("collectors.base_product_collector.logger", mock_logger)

    collector = DummyCollector(str(tmp_path))
    await collector.client.aclose()

    mock_client = AsyncMock()
    collector.client = mock_client

    mock_response = SimpleNamespace(content=b"image-bytes")
    mock_response.raise_for_status = lambda: None

    mock_client.get.return_value = mock_response

    image_path = await collector.download_image(
        "https://example.com/image.jpg", "product-1", "image-1"
    )

    expected_path = Path(tmp_path) / "products" / "product-1" / "image-1.jpg"
    assert image_path == str(expected_path)
    assert expected_path.read_bytes() == b"image-bytes"
    mock_logger.warning.assert_called_once()
    warning_args, warning_kwargs = mock_logger.warning.call_args
    assert warning_args[0] == "Saved image without Pillow post-processing"
    assert warning_kwargs["image_id"] == "image-1"
    assert warning_kwargs["path"] == str(expected_path)


@pytest.mark.asyncio
async def test_download_image_handles_download_error(monkeypatch, tmp_path):
    monkeypatch.setattr("collectors.base_product_collector.Image", None)
    mock_logger = MagicMock()
    monkeypatch.setattr("collectors.base_product_collector.logger", mock_logger)

    collector = DummyCollector(str(tmp_path))
    await collector.client.aclose()

    mock_client = AsyncMock()
    collector.client = mock_client
    mock_client.get.side_effect = httpx.HTTPError("boom")

    image_path = await collector.download_image(
        "https://example.com/404.jpg", "product-2", "image-2"
    )

    assert image_path is None
    mock_logger.error.assert_called_once()
    error_args, error_kwargs = mock_logger.error.call_args
    assert error_args[0] == "Failed to download image"
    assert error_kwargs["image_url"] == "https://example.com/404.jpg"
    assert error_kwargs["image_id"] == "image-2"
