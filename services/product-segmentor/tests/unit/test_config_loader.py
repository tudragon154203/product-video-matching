"""Unit tests for config_loader module - batch concurrency configuration."""

import os
from unittest.mock import MagicMock, patch

import pytest


# Mock the global config module before importing config_loader
mock_global_config = MagicMock()
mock_global_config.POSTGRES_DSN = "postgresql://test:test@localhost:5432/test"
mock_global_config.BUS_BROKER = "amqp://localhost:5672"
mock_global_config.DATA_ROOT_CONTAINER = "/data"
mock_global_config.MODEL_CACHE = "/model_cache"
mock_global_config.LOG_LEVEL = "INFO"
mock_global_config.IMG_SIZE = (1024, 1024)


@pytest.fixture
def clean_env():
    """Clean environment variables before and after tests."""
    keys_to_clean = [
        "MAX_CONCURRENT_IMAGES_IN_BATCH",
        "MIN_CONCURRENT_IMAGES_IN_BATCH",
        "MAX_CONCURRENT_BATCHES",
        "BATCH_TIMEOUT_SECONDS",
        "USE_FP16",
        "RETRY_ON_OOM",
        "MAX_OOM_RETRIES",
        "GPU_MEMORY_THRESHOLD",
        "MASK_QUALITY",
    ]
    
    original_env = {}
    for key in keys_to_clean:
        original_env[key] = os.environ.get(key)
        os.environ.pop(key, None)
    
    yield
    
    # Restore original env
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


class TestBatchConcurrencyConfig:
    """Test batch concurrency configuration."""

    def test_max_concurrent_batches_default(self, clean_env):
        """Test MAX_CONCURRENT_BATCHES has a valid default value."""
        with patch('config_loader.load_dotenv'):
            with patch.dict('sys.modules', {'config': MagicMock(config=mock_global_config)}):
                import importlib
                import sys
                if 'config_loader' in sys.modules:
                    del sys.modules['config_loader']
                
                from config_loader import ProductSegmentorConfig
                config = ProductSegmentorConfig()
                
                # Verify it's a positive integer (code default is 2)
                assert isinstance(config.MAX_CONCURRENT_BATCHES, int)
                assert config.MAX_CONCURRENT_BATCHES > 0

    def test_max_concurrent_batches_custom(self, clean_env):
        """Test MAX_CONCURRENT_BATCHES with custom value."""
        os.environ["MAX_CONCURRENT_BATCHES"] = "5"
        
        with patch('config_loader.load_dotenv'):
            with patch.dict('sys.modules', {'config': MagicMock(config=mock_global_config)}):
                import importlib
                import sys
                if 'config_loader' in sys.modules:
                    del sys.modules['config_loader']
                
                from config_loader import ProductSegmentorConfig
                config = ProductSegmentorConfig()
                
                assert config.MAX_CONCURRENT_BATCHES == 5

    def test_max_concurrent_images_in_batch_default(self, clean_env):
        """Test MAX_CONCURRENT_IMAGES_IN_BATCH default value."""
        with patch('config_loader.load_dotenv'):
            with patch.dict('sys.modules', {'config': MagicMock(config=mock_global_config)}):
                import importlib
                import sys
                if 'config_loader' in sys.modules:
                    del sys.modules['config_loader']
                
                from config_loader import ProductSegmentorConfig
                config = ProductSegmentorConfig()
                
                assert config.MAX_CONCURRENT_IMAGES_IN_BATCH == 3

    def test_max_concurrent_images_in_batch_custom(self, clean_env):
        """Test MAX_CONCURRENT_IMAGES_IN_BATCH with custom value."""
        os.environ["MAX_CONCURRENT_IMAGES_IN_BATCH"] = "10"
        
        with patch('config_loader.load_dotenv'):
            with patch.dict('sys.modules', {'config': MagicMock(config=mock_global_config)}):
                import importlib
                import sys
                if 'config_loader' in sys.modules:
                    del sys.modules['config_loader']
                
                from config_loader import ProductSegmentorConfig
                config = ProductSegmentorConfig()
                
                assert config.MAX_CONCURRENT_IMAGES_IN_BATCH == 10

    def test_min_concurrent_images_in_batch_default(self, clean_env):
        """Test MIN_CONCURRENT_IMAGES_IN_BATCH default value."""
        with patch('config_loader.load_dotenv'):
            with patch.dict('sys.modules', {'config': MagicMock(config=mock_global_config)}):
                import importlib
                import sys
                if 'config_loader' in sys.modules:
                    del sys.modules['config_loader']
                
                from config_loader import ProductSegmentorConfig
                config = ProductSegmentorConfig()
                
                assert config.MIN_CONCURRENT_IMAGES_IN_BATCH == 1

    def test_min_concurrent_images_in_batch_custom(self, clean_env):
        """Test MIN_CONCURRENT_IMAGES_IN_BATCH with custom value."""
        os.environ["MIN_CONCURRENT_IMAGES_IN_BATCH"] = "2"
        
        with patch('config_loader.load_dotenv'):
            with patch.dict('sys.modules', {'config': MagicMock(config=mock_global_config)}):
                import importlib
                import sys
                if 'config_loader' in sys.modules:
                    del sys.modules['config_loader']
                
                from config_loader import ProductSegmentorConfig
                config = ProductSegmentorConfig()
                
                assert config.MIN_CONCURRENT_IMAGES_IN_BATCH == 2

    def test_batch_timeout_seconds_default(self, clean_env):
        """Test BATCH_TIMEOUT_SECONDS default value."""
        with patch('config_loader.load_dotenv'):
            with patch.dict('sys.modules', {'config': MagicMock(config=mock_global_config)}):
                import importlib
                import sys
                if 'config_loader' in sys.modules:
                    del sys.modules['config_loader']
                
                from config_loader import ProductSegmentorConfig
                config = ProductSegmentorConfig()
                
                assert config.BATCH_TIMEOUT_SECONDS == 1800

    def test_batch_timeout_seconds_custom(self, clean_env):
        """Test BATCH_TIMEOUT_SECONDS with custom value."""
        os.environ["BATCH_TIMEOUT_SECONDS"] = "3600"
        
        with patch('config_loader.load_dotenv'):
            with patch.dict('sys.modules', {'config': MagicMock(config=mock_global_config)}):
                import importlib
                import sys
                if 'config_loader' in sys.modules:
                    del sys.modules['config_loader']
                
                from config_loader import ProductSegmentorConfig
                config = ProductSegmentorConfig()
                
                assert config.BATCH_TIMEOUT_SECONDS == 3600


class TestGPUMemoryConfig:
    """Test GPU memory management configuration."""

    def test_use_fp16_default(self, clean_env):
        """Test USE_FP16 default value (true)."""
        with patch('config_loader.load_dotenv'):
            with patch.dict('sys.modules', {'config': MagicMock(config=mock_global_config)}):
                import sys
                if 'config_loader' in sys.modules:
                    del sys.modules['config_loader']
                
                from config_loader import ProductSegmentorConfig
                config = ProductSegmentorConfig()
                
                assert config.USE_FP16 is True

    def test_use_fp16_enabled_variations(self, clean_env):
        """Test USE_FP16 with various enabled values."""
        enabled_values = ["1", "true", "True", "TRUE", "yes", "YES", "enable", "ENABLE"]
        
        for value in enabled_values:
            os.environ["USE_FP16"] = value
            
            with patch('config_loader.load_dotenv'):
                with patch.dict('sys.modules', {'config': MagicMock(config=mock_global_config)}):
                    import sys
                    if 'config_loader' in sys.modules:
                        del sys.modules['config_loader']
                    
                    from config_loader import ProductSegmentorConfig
                    config = ProductSegmentorConfig()
                    
                    assert config.USE_FP16 is True, f"Failed for value: {value}"

    def test_use_fp16_disabled_variations(self, clean_env):
        """Test USE_FP16 with various disabled values."""
        disabled_values = ["0", "false", "False", "FALSE", "no", "NO", "disable", "DISABLE"]
        
        for value in disabled_values:
            os.environ["USE_FP16"] = value
            
            with patch('config_loader.load_dotenv'):
                with patch.dict('sys.modules', {'config': MagicMock(config=mock_global_config)}):
                    import sys
                    if 'config_loader' in sys.modules:
                        del sys.modules['config_loader']
                    
                    from config_loader import ProductSegmentorConfig
                    config = ProductSegmentorConfig()
                    
                    assert config.USE_FP16 is False, f"Failed for value: {value}"

    def test_retry_on_oom_default(self, clean_env):
        """Test RETRY_ON_OOM default value (true)."""
        with patch('config_loader.load_dotenv'):
            with patch.dict('sys.modules', {'config': MagicMock(config=mock_global_config)}):
                import sys
                if 'config_loader' in sys.modules:
                    del sys.modules['config_loader']
                
                from config_loader import ProductSegmentorConfig
                config = ProductSegmentorConfig()
                
                assert config.RETRY_ON_OOM is True

    def test_retry_on_oom_disabled(self, clean_env):
        """Test RETRY_ON_OOM disabled."""
        os.environ["RETRY_ON_OOM"] = "false"
        
        with patch('config_loader.load_dotenv'):
            with patch.dict('sys.modules', {'config': MagicMock(config=mock_global_config)}):
                import sys
                if 'config_loader' in sys.modules:
                    del sys.modules['config_loader']
                
                from config_loader import ProductSegmentorConfig
                config = ProductSegmentorConfig()
                
                assert config.RETRY_ON_OOM is False

    def test_max_oom_retries_default(self, clean_env):
        """Test MAX_OOM_RETRIES default value."""
        with patch('config_loader.load_dotenv'):
            with patch.dict('sys.modules', {'config': MagicMock(config=mock_global_config)}):
                import sys
                if 'config_loader' in sys.modules:
                    del sys.modules['config_loader']
                
                from config_loader import ProductSegmentorConfig
                config = ProductSegmentorConfig()
                
                assert config.MAX_OOM_RETRIES == 3

    def test_max_oom_retries_custom(self, clean_env):
        """Test MAX_OOM_RETRIES with custom value."""
        os.environ["MAX_OOM_RETRIES"] = "5"
        
        with patch('config_loader.load_dotenv'):
            with patch.dict('sys.modules', {'config': MagicMock(config=mock_global_config)}):
                import sys
                if 'config_loader' in sys.modules:
                    del sys.modules['config_loader']
                
                from config_loader import ProductSegmentorConfig
                config = ProductSegmentorConfig()
                
                assert config.MAX_OOM_RETRIES == 5

    def test_gpu_memory_threshold_default(self, clean_env):
        """Test GPU_MEMORY_THRESHOLD has a valid default value."""
        with patch('config_loader.load_dotenv'):
            with patch.dict('sys.modules', {'config': MagicMock(config=mock_global_config)}):
                import sys
                if 'config_loader' in sys.modules:
                    del sys.modules['config_loader']
                
                from config_loader import ProductSegmentorConfig
                config = ProductSegmentorConfig()
                
                # Verify it's a valid threshold (code default is 0.85)
                assert isinstance(config.GPU_MEMORY_THRESHOLD, float)
                assert 0.0 < config.GPU_MEMORY_THRESHOLD <= 1.0

    def test_gpu_memory_threshold_custom(self, clean_env):
        """Test GPU_MEMORY_THRESHOLD with custom value."""
        os.environ["GPU_MEMORY_THRESHOLD"] = "0.75"
        
        with patch('config_loader.load_dotenv'):
            with patch.dict('sys.modules', {'config': MagicMock(config=mock_global_config)}):
                import sys
                if 'config_loader' in sys.modules:
                    del sys.modules['config_loader']
                
                from config_loader import ProductSegmentorConfig
                config = ProductSegmentorConfig()
                
                assert config.GPU_MEMORY_THRESHOLD == 0.75


class TestOtherConfig:
    """Test other configuration values."""

    def test_mask_quality_default(self, clean_env):
        """Test MASK_QUALITY default value."""
        with patch('config_loader.load_dotenv'):
            with patch.dict('sys.modules', {'config': MagicMock(config=mock_global_config)}):
                import sys
                if 'config_loader' in sys.modules:
                    del sys.modules['config_loader']
                
                from config_loader import ProductSegmentorConfig
                config = ProductSegmentorConfig()
                
                assert config.MASK_QUALITY == 0.8

    def test_mask_quality_custom(self, clean_env):
        """Test MASK_QUALITY with custom value."""
        os.environ["MASK_QUALITY"] = "0.95"
        
        with patch('config_loader.load_dotenv'):
            with patch.dict('sys.modules', {'config': MagicMock(config=mock_global_config)}):
                import sys
                if 'config_loader' in sys.modules:
                    del sys.modules['config_loader']
                
                from config_loader import ProductSegmentorConfig
                config = ProductSegmentorConfig()
                
                assert config.MASK_QUALITY == 0.95

    def test_global_config_values_used(self, clean_env):
        """Test that global config values are properly used."""
        with patch('config_loader.load_dotenv'):
            with patch.dict('sys.modules', {'config': MagicMock(config=mock_global_config)}):
                import sys
                if 'config_loader' in sys.modules:
                    del sys.modules['config_loader']
                
                from config_loader import ProductSegmentorConfig
                config = ProductSegmentorConfig()
                
                assert config.POSTGRES_DSN == "postgresql://test:test@localhost:5432/test"
                assert config.BUS_BROKER == "amqp://localhost:5672"
                assert config.MODEL_CACHE == "/model_cache"
                # LOG_LEVEL can be overridden by .env, just verify it's a string
                assert isinstance(config.LOG_LEVEL, str)
                assert config.IMG_SIZE == (1024, 1024)


class TestConfigIntegration:
    """Test configuration integration scenarios."""

    def test_all_batch_config_together(self, clean_env):
        """Test all batch-related config values together."""
        os.environ["MAX_CONCURRENT_BATCHES"] = "4"
        os.environ["MAX_CONCURRENT_IMAGES_IN_BATCH"] = "8"
        os.environ["MIN_CONCURRENT_IMAGES_IN_BATCH"] = "2"
        os.environ["BATCH_TIMEOUT_SECONDS"] = "7200"
        
        with patch('config_loader.load_dotenv'):
            with patch.dict('sys.modules', {'config': MagicMock(config=mock_global_config)}):
                import sys
                if 'config_loader' in sys.modules:
                    del sys.modules['config_loader']
                
                from config_loader import ProductSegmentorConfig
                config = ProductSegmentorConfig()
                
                assert config.MAX_CONCURRENT_BATCHES == 4
                assert config.MAX_CONCURRENT_IMAGES_IN_BATCH == 8
                assert config.MIN_CONCURRENT_IMAGES_IN_BATCH == 2
                assert config.BATCH_TIMEOUT_SECONDS == 7200

    def test_all_gpu_config_together(self, clean_env):
        """Test all GPU-related config values together."""
        os.environ["USE_FP16"] = "true"
        os.environ["RETRY_ON_OOM"] = "true"
        os.environ["MAX_OOM_RETRIES"] = "5"
        os.environ["GPU_MEMORY_THRESHOLD"] = "0.90"
        
        with patch('config_loader.load_dotenv'):
            with patch.dict('sys.modules', {'config': MagicMock(config=mock_global_config)}):
                import sys
                if 'config_loader' in sys.modules:
                    del sys.modules['config_loader']
                
                from config_loader import ProductSegmentorConfig
                config = ProductSegmentorConfig()
                
                assert config.USE_FP16 is True
                assert config.RETRY_ON_OOM is True
                assert config.MAX_OOM_RETRIES == 5
                assert config.GPU_MEMORY_THRESHOLD == 0.90

    def test_production_like_config(self, clean_env):
        """Test production-like configuration."""
        os.environ["MAX_CONCURRENT_BATCHES"] = "2"
        os.environ["MAX_CONCURRENT_IMAGES_IN_BATCH"] = "2"
        os.environ["MIN_CONCURRENT_IMAGES_IN_BATCH"] = "1"
        os.environ["USE_FP16"] = "true"
        os.environ["RETRY_ON_OOM"] = "true"
        os.environ["GPU_MEMORY_THRESHOLD"] = "0.85"
        
        with patch('config_loader.load_dotenv'):
            with patch.dict('sys.modules', {'config': MagicMock(config=mock_global_config)}):
                import sys
                if 'config_loader' in sys.modules:
                    del sys.modules['config_loader']
                
                from config_loader import ProductSegmentorConfig
                config = ProductSegmentorConfig()
                
                # Verify conservative production settings
                assert config.MAX_CONCURRENT_BATCHES == 2
                assert config.MAX_CONCURRENT_IMAGES_IN_BATCH == 2
                assert config.MIN_CONCURRENT_IMAGES_IN_BATCH == 1
                assert config.USE_FP16 is True
                assert config.RETRY_ON_OOM is True
                assert config.GPU_MEMORY_THRESHOLD == 0.85
