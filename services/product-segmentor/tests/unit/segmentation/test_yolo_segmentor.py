"""Unit tests for YOLOSegmentor model download and caching behavior."""

import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from pathlib import Path

import pytest

from segmentation.models.yolo_segmentor import YOLOSegmentor

pytestmark = pytest.mark.unit


class TestYOLOSegmentor:
    """Test YOLOSegmentor initialization, caching, and download behavior."""

    @pytest.fixture
    def temp_model_cache(self):
        """Create temporary directory for model cache testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_ultralytics_yolo(self):
        """Mock ultralytics YOLO class."""
        with patch('segmentation.models.yolo_segmentor.YOLO') as mock_yolo_class:
            mock_model = MagicMock()
            mock_yolo_class.return_value = mock_model
            yield mock_yolo_class, mock_model

    def test_model_path_resolution_docker_environment(self):
        """Test model path resolution in Docker environment."""
        with patch('os.path.exists') as mock_exists:
            # Simulate Docker environment
            mock_exists.side_effect = lambda path: path == '/app/model_cache'

            segmentor = YOLOSegmentor('yolo11l-seg')

            assert segmentor._model_cache_dir == '/app/model_cache'
            # Use os.path.normpath to handle path separator differences
            expected_path = os.path.normpath('/app/model_cache/yolo11l-seg.pt')
            assert os.path.normpath(segmentor._model_path) == expected_path
            assert segmentor._model_name == 'yolo11l-seg'

    def test_model_path_resolution_local_development(self, temp_model_cache):
        """Test model path resolution in local development."""
        with patch('segmentation.models.yolo_segmentor.config') as mock_config:
            mock_config.MODEL_CACHE = temp_model_cache

            segmentor = YOLOSegmentor('yolo11l-seg')

            assert segmentor._model_cache_dir == temp_model_cache
            assert segmentor._model_path == os.path.join(temp_model_cache, 'yolo11l-seg.pt')
            assert segmentor._model_name == 'yolo11l-seg'

    def test_model_name_with_extension(self, temp_model_cache):
        """Test model name handling with .pt extension."""
        with patch('segmentation.models.yolo_segmentor.config') as mock_config:
            mock_config.MODEL_CACHE = temp_model_cache

            segmentor = YOLOSegmentor('yolo11l-seg.pt')

            assert segmentor._model_name == 'yolo11l-seg.pt'
            assert segmentor._model_path == os.path.join(temp_model_cache, 'yolo11l-seg.pt')

    @pytest.mark.asyncio
    async def test_initialize_with_existing_model(self, temp_model_cache, mock_ultralytics_yolo):
        """Test initialization when model already exists in cache."""
        mock_yolo_class, mock_model = mock_ultralytics_yolo

        # Create existing model file
        existing_model_path = os.path.join(temp_model_cache, 'yolo11l-seg.pt')
        Path(existing_model_path).touch()

        with patch('segmentation.models.yolo_segmentor.config') as mock_config:
            mock_config.MODEL_CACHE = temp_model_cache

            segmentor = YOLOSegmentor('yolo11l-seg')
            await segmentor.initialize()

            # Should load from existing file
            mock_yolo_class.assert_called_once_with(existing_model_path)
            assert segmentor._initialized
            assert segmentor._model == mock_model

    @pytest.mark.asyncio
    async def test_initialize_downloads_to_correct_directory(self, temp_model_cache, mock_ultralytics_yolo):
        """Test that model downloads to correct cache directory."""
        mock_yolo_class, mock_model = mock_ultralytics_yolo

        with patch('segmentation.models.yolo_segmentor.config') as mock_config:
            mock_config.MODEL_CACHE = temp_model_cache

            # Mock os.chdir to track directory changes
            with patch('os.chdir') as mock_chdir:
                with patch('os.getcwd') as mock_getcwd:
                    original_cwd = "/original/working/directory"
                    mock_getcwd.return_value = original_cwd

                    segmentor = YOLOSegmentor('yolo11l-seg')
                    await segmentor.initialize()

                    # Should change to cache directory and back (use call_args_list for proper comparison)
                    calls = mock_chdir.call_args_list
                    assert len(calls) == 2
                    assert calls[0][0][0] == temp_model_cache  # First call: change to cache dir
                    assert calls[1][0][0] == original_cwd   # Second call: change back to original

                    # Should initialize YOLO from cache directory
                    mock_yolo_class.assert_called_once_with('yolo11l-seg')

                    assert segmentor._initialized

    @pytest.mark.asyncio
    async def test_download_creates_model_in_cache_not_cwd(self, temp_model_cache):
        """Test that downloaded model appears in cache directory, not current working directory."""
        original_cwd = os.getcwd()

        with patch('segmentation.models.yolo_segmentor.config') as mock_config:
            mock_config.MODEL_CACHE = temp_model_cache

            # Create a real mock that simulates file creation
            with patch('segmentation.models.yolo_segmentor.YOLO') as mock_yolo_class:
                def create_model_file(model_name):
                    """Simulate YOLO creating model file in current directory."""
                    # This simulates ultralytics downloading to current directory
                    model_filename = f"{model_name}.pt"
                    with open(model_filename, 'w') as f:
                        f.write("mock model data")

                mock_yolo_class.side_effect = create_model_file

                segmentor = YOLOSegmentor('yolo11l-seg')
                await segmentor.initialize()

                # Model should be in cache directory
                cache_model_path = os.path.join(temp_model_cache, 'yolo11l-seg.pt')
                assert os.path.exists(cache_model_path), f"Model not found in cache at {cache_model_path}"

                # Model should NOT be in original working directory
                cwd_model_path = os.path.join(original_cwd, 'yolo11l-seg.pt')
                assert not os.path.exists(cwd_model_path), f"Model incorrectly found in CWD at {cwd_model_path}"

                # Clean up if somehow created in CWD
                if os.path.exists(cwd_model_path):
                    os.remove(cwd_model_path)

    @pytest.mark.asyncio
    async def test_download_handles_path_mismatch(self, temp_model_cache, mock_ultralytics_yolo):
        """Test handling when download creates file at unexpected path."""
        mock_yolo_class, mock_model = mock_ultralytics_yolo

        with patch('segmentation.models.yolo_segmentor.config') as mock_config:
            mock_config.MODEL_CACHE = temp_model_cache

            # Simulate ultralytics creating file with different naming
            model_path = os.path.join(temp_model_cache, 'yolo11l-seg.pt')

            # Create file at location
            Path(model_path).touch()

            with patch('os.path.exists') as mock_exists:
                mock_exists.side_effect = lambda path: path == model_path

                with patch('os.rename') as mock_rename:
                    segmentor = YOLOSegmentor('yolo11l-seg')
                    await segmentor.initialize()

                    # Should not rename since paths are same
                    mock_rename.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_restores_working_directory_on_error(self, temp_model_cache):
        """Test that working directory is restored even if initialization fails."""
        original_cwd = os.getcwd()

        with patch('segmentation.models.yolo_segmentor.config') as mock_config:
            mock_config.MODEL_CACHE = temp_model_cache

            # Make YOLO raise an exception
            with patch('segmentation.models.yolo_segmentor.YOLO', side_effect=Exception("Download failed")):
                with patch('os.chdir') as mock_chdir:
                    segmentor = YOLOSegmentor('yolo11l-seg')

                    with pytest.raises(Exception, match="Download failed"):
                        await segmentor.initialize()

                    # Should still restore working directory (use call_args_list for proper comparison)
                    calls = mock_chdir.call_args_list
                    assert len(calls) == 2
                    assert calls[0][0][0] == temp_model_cache  # First call: change to cache dir
                    assert calls[1][0][0] == original_cwd   # Second call: change back to original

                    # Should not be initialized
                    assert not segmentor._initialized

    @pytest.mark.asyncio
    async def test_segment_image_requires_initialization(self, temp_model_cache):
        """Test that segment_image raises error if not initialized."""
        with patch('segmentation.models.yolo_segmentor.config') as mock_config:
            mock_config.MODEL_CACHE = temp_model_cache

            segmentor = YOLOSegmentor('yolo11l-seg')
            # Don't initialize

            with pytest.raises(Exception, match="YOLO segmentor not initialized"):
                await segmentor.segment_image("test_image.jpg")

    @pytest.mark.asyncio
    async def test_segment_image_missing_file(self, temp_model_cache, mock_ultralytics_yolo):
        """Test segment_image with missing image file."""
        mock_yolo_class, mock_model = mock_ultralytics_yolo

        # Setup mock model prediction
        mock_model.predict.return_value = []

        with patch('segmentation.models.yolo_segmentor.config') as mock_config:
            mock_config.MODEL_CACHE = temp_model_cache

            segmentor = YOLOSegmentor('yolo11l-seg')
            await segmentor.initialize()

            with pytest.raises(FileNotFoundError, match="Image file not found"):
                await segmentor.segment_image("/nonexistent/image.jpg")

    @pytest.mark.asyncio
    async def test_segment_image_no_persons_detected(self, temp_model_cache, mock_ultralytics_yolo):
        """Test segment_image when no persons are detected."""
        mock_yolo_class, mock_model = mock_ultralytics_yolo

        # Mock prediction result with no masks
        mock_result = MagicMock()
        mock_result.masks = None
        mock_model.predict.return_value = [mock_result]

        with patch('segmentation.models.yolo_segmentor.config') as mock_config:
            mock_config.MODEL_CACHE = temp_model_cache

            segmentor = YOLOSegmentor('yolo11l-seg')
            await segmentor.initialize()

            # Create test image file
            test_image = os.path.join(temp_model_cache, 'test.jpg')
            Path(test_image).touch()

            result = await segmentor.segment_image(test_image)

            # Should return None when no persons detected
            assert result is None
            mock_model.predict.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_resets_state(self, temp_model_cache, mock_ultralytics_yolo):
        """Test cleanup method properly resets state."""
        mock_yolo_class, mock_model = mock_ultralytics_yolo

        with patch('segmentation.models.yolo_segmentor.config') as mock_config:
            mock_config.MODEL_CACHE = temp_model_cache

            segmentor = YOLOSegmentor('yolo11l-seg')
            await segmentor.initialize()

            assert segmentor._initialized
            assert segmentor._model == mock_model

            segmentor.cleanup()

            assert not segmentor._initialized
            assert segmentor._model is None

    def test_model_name_property(self, temp_model_cache):
        """Test model_name property returns correct value."""
        with patch('segmentation.models.yolo_segmentor.config') as mock_config:
            mock_config.MODEL_CACHE = temp_model_cache

            segmentor = YOLOSegmentor('test-model')
            assert segmentor.model_name == 'test-model'

    def test_is_initialized_property(self, temp_model_cache):
        """Test is_initialized property reflects initialization state."""
        with patch('segmentation.models.yolo_segmentor.config') as mock_config:
            mock_config.MODEL_CACHE = temp_model_cache

            segmentor = YOLOSegmentor('test-model')
            assert not segmentor.is_initialized

            segmentor._initialized = True
            assert segmentor.is_initialized
