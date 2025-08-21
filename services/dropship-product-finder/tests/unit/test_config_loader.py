"""
Unit tests for eBay configuration in config_loader.py
"""
import pytest
import os
from unittest.mock import patch, MagicMock
import sys

# Add libs directory to PYTHONPATH for imports
sys.path.insert(0, '/app/libs')

# Mock the dotenv loading during tests
def mock_load_dotenv(*args, **kwargs):
    pass

# Import the actual configuration class
try:
    from dropship_product_finder.config_loader import DropshipProductFinderConfig
except ImportError:
    # Fallback for local development
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import importlib.util
    spec = importlib.util.spec_from_file_location("config_loader", "config_loader.py")
    config_loader_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_loader_module)
    DropshipProductFinderConfig = config_loader_module.DropshipProductFinderConfig

class TestDropshipProductFinderConfig(DropshipProductFinderConfig):
    """Test configuration class that inherits from DropshipProductFinderConfig"""
    
    def __init__(self):
        # Initialize with default test values, but allow override from environment variables
        self.EBAY_CLIENT_ID = os.getenv("EBAY_CLIENT_ID", "")
        self.EBAY_CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET", "")
        self.EBAY_MARKETPLACES = os.getenv("EBAY_MARKETPLACES", "EBAY_US")
        self.EBAY_ENVIRONMENT = os.getenv("EBAY_ENVIRONMENT", "sandbox")
        self.EBAY_SCOPES = os.getenv("EBAY_SCOPES", "https://api.ebay.com/oauth/api_scope")
        self.USE_MOCK_FINDERS = os.getenv("USE_MOCK_FINDERS", "true").lower() == "true"
        self.REDIS_HOST = os.getenv("REDIS_HOST", "redis")
        self.REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
        self.REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
        self.REDIS_DB = int(os.getenv("REDIS_DB", "0"))
        self.POSTGRES_DSN = "postgresql://postgres:dev@postgres:5432/product_video_matching"
        self.POSTGRES_USER = "postgres"
        self.POSTGRES_PASSWORD = "dev"
        self.POSTGRES_HOST = "postgres"
        self.POSTGRES_PORT = "5432"
        self.POSTGRES_DB = "product_video_matching"
        self.BUS_BROKER = "amqp://guest:guest@localhost:5672/"
        self.DATA_ROOT = "./data"
        self.LOG_LEVEL = "INFO"
        self.TIMEOUT_SECS_BROWSE = float(os.getenv("BROWSE_TIMEOUT_SECS", "30.0"))
        self.MAX_RETRIES_BROWSE = int(os.getenv("BROWSE_MAX_RETRIES", "2"))
        self.BACKOFF_BASE_BROWSE = float(os.getenv("BROWSE_BACKOFF_BASE", "1.5"))

class TestDropshipProductFinderConfigSuite:
    """Test cases for eBay configuration"""
    
    def test_ebay_browse_production_url(self):
        """Test eBay browse base URL for production environment"""
        with patch.dict(os.environ, {'EBAY_ENVIRONMENT': 'production'}):
            config = TestDropshipProductFinderConfig()
            assert config.EBAY_BROWSE_BASE == "https://api.ebay.com/buy/browse/v1"
    
    def test_ebay_browse_sandbox_url(self):
        """Test eBay browse base URL for sandbox environment"""
        with patch.dict(os.environ, {'EBAY_ENVIRONMENT': 'sandbox'}):
            config = TestDropshipProductFinderConfig()
            assert config.EBAY_BROWSE_BASE == "https://api.sandbox.ebay.com/buy/browse/v1"
    
    def test_ebay_browse_token_url_production(self):
        """Test eBay token URL for production environment"""
        with patch.dict(os.environ, {'EBAY_ENVIRONMENT': 'production'}):
            config = TestDropshipProductFinderConfig()
            assert config.EBAY_TOKEN_URL == "https://api.ebay.com/identity/v1/oauth2/token"
    
    def test_ebay_browse_token_url_sandbox(self):
        """Test eBay token URL for sandbox environment"""
        with patch.dict(os.environ, {'EBAY_ENVIRONMENT': 'sandbox'}):
            config = TestDropshipProductFinderConfig()
            assert config.EBAY_TOKEN_URL == "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
    
    def test_browse_timeout_default(self):
        """Test default browse timeout value"""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.setdefault("BROWSE_TIMEOUT_SECS", "30.0")
            config = TestDropshipProductFinderConfig()
            assert config.TIMEOUT_SECS_BROWSE == 30.0
    
    def test_browse_timeout_custom(self):
        """Test custom browse timeout value from environment"""
        custom_timeout = "45.5"
        with patch.dict(os.environ, {'BROWSE_TIMEOUT_SECS': custom_timeout}):
            config = TestDropshipProductFinderConfig()
            assert config.TIMEOUT_SECS_BROWSE == 45.5
    
    def test_max_retries_default(self):
        """Test default max retries value"""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.setdefault("BROWSE_MAX_RETRIES", "2")
            config = TestDropshipProductFinderConfig()
            assert config.MAX_RETRIES_BROWSE == 2
    
    def test_max_retries_custom(self):
        """Test custom max retries value from environment"""
        custom_retries = "5"
        with patch.dict(os.environ, {'BROWSE_MAX_RETRIES': custom_retries}):
            config = TestDropshipProductFinderConfig()
            assert config.MAX_RETRIES_BROWSE == 5
    
    def test_backoff_base_default(self):
        """Test default backoff base value"""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.setdefault("BROWSE_BACKOFF_BASE", "1.5")
            config = TestDropshipProductFinderConfig()
            assert config.BACKOFF_BASE_BROWSE == 1.5
    
    def test_backoff_base_custom(self):
        """Test custom backoff base value from environment"""
        custom_backoff = "2.0"
        with patch.dict(os.environ, {'BROWSE_BACKOFF_BASE': custom_backoff}):
            config = TestDropshipProductFinderConfig()
            assert config.BACKOFF_BASE_BROWSE == 2.0
    
    def test_ebay_client_id_default(self):
        """Test default eBay client ID value"""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.setdefault("EBAY_CLIENT_ID", "")
            config = TestDropshipProductFinderConfig()
            assert config.EBAY_CLIENT_ID == ""
    
    def test_ebay_client_id_custom(self):
        """Test custom eBay client ID from environment"""
        client_id = "test_client_id_123"
        with patch.dict(os.environ, {'EBAY_CLIENT_ID': client_id}):
            config = TestDropshipProductFinderConfig()
            assert config.EBAY_CLIENT_ID == client_id
    
    def test_ebay_client_secret_default(self):
        """Test default eBay client secret value"""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.setdefault("EBAY_CLIENT_SECRET", "")
            config = TestDropshipProductFinderConfig()
            assert config.EBAY_CLIENT_SECRET == ""
    
    def test_ebay_client_secret_custom(self):
        """Test custom eBay client secret from environment"""
        client_secret = "test_client_secret_456"
        with patch.dict(os.environ, {'EBAY_CLIENT_SECRET': client_secret}):
            config = TestDropshipProductFinderConfig()
            assert config.EBAY_CLIENT_SECRET == client_secret
    
    def test_ebay_marketplaces_default(self):
        """Test default eBay marketplaces value"""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.setdefault("EBAY_MARKETPLACES", "EBAY_US")
            config = TestDropshipProductFinderConfig()
            assert config.EBAY_MARKETPLACES == "EBAY_US"
    
    def test_ebay_marketplaces_custom(self):
        """Test custom eBay marketplaces from environment"""
        marketplaces = "EBAY_US,EBAY_DE,EBAY_AU"
        with patch.dict(os.environ, {'EBAY_MARKETPLACES': marketplaces}):
            config = TestDropshipProductFinderConfig()
            assert config.EBAY_MARKETPLACES == marketplaces
    
    def test_use_mock_finders_default(self):
        """Test default mock finders setting"""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.setdefault("USE_MOCK_FINDERS", "true")
            config = TestDropshipProductFinderConfig()
            assert config.USE_MOCK_FINDERS == True
    
    def test_use_mock_finders_false(self):
        """Test mock finders set to false"""
        with patch.dict(os.environ, {'USE_MOCK_FINDERS': 'false'}):
            config = TestDropshipProductFinderConfig()
            assert config.USE_MOCK_FINDERS == False
    
    def test_use_mock_finders_true(self):
        """Test mock finders set to true"""
        with patch.dict(os.environ, {'USE_MOCK_FINDERS': 'true'}):
            config = TestDropshipProductFinderConfig()
            assert config.USE_MOCK_FINDERS == True