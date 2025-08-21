"""
Unit tests for eBay configuration in config_loader.py
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from config_loader import DropshipProductFinderConfig


class TestDropshipProductFinderConfig:
    """Test cases for eBay configuration"""
    
    def test_ebay_browse_production_url(self):
        """Test eBay browse base URL for production environment"""
        with patch.dict(os.environ, {'EBAY_ENVIRONMENT': 'production'}):
            config = DropshipProductFinderConfig()
            assert config.EBAY_BROWSE_BASE == "https://api.ebay.com/buy/browse/v1"
    
    def test_ebay_browse_sandbox_url(self):
        """Test eBay browse base URL for sandbox environment"""
        with patch.dict(os.environ, {'EBAY_ENVIRONMENT': 'sandbox'}):
            config = DropshipProductFinderConfig()
            assert config.EBAY_BROWSE_BASE == "https://api.sandbox.ebay.com/buy/browse/v1"
    
    def test_ebay_browse_token_url_production(self):
        """Test eBay token URL for production environment"""
        with patch.dict(os.environ, {'EBAY_ENVIRONMENT': 'production'}):
            config = DropshipProductFinderConfig()
            assert config.EBAY_TOKEN_URL == "https://api.ebay.com/identity/v1/oauth2/token"
    
    def test_ebay_browse_token_url_sandbox(self):
        """Test eBay token URL for sandbox environment"""
        with patch.dict(os.environ, {'EBAY_ENVIRONMENT': 'sandbox'}):
            config = DropshipProductFinderConfig()
            assert config.EBAY_TOKEN_URL == "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
    
    def test_browse_timeout_default(self):
        """Test default browse timeout value"""
        with patch.dict(os.environ, {}, clear=True):
            config = DropshipProductFinderConfig()
            assert config.TIMEOUT_SECS_BROWSE == 30.0
    
    def test_browse_timeout_custom(self):
        """Test custom browse timeout value from environment"""
        custom_timeout = "45.5"
        with patch.dict(os.environ, {'BROWSE_TIMEOUT_SECS': custom_timeout}):
            config = DropshipProductFinderConfig()
            assert config.TIMEOUT_SECS_BROWSE == 45.5
    
    def test_max_retries_default(self):
        """Test default max retries value"""
        with patch.dict(os.environ, {}, clear=True):
            config = DropshipProductFinderConfig()
            assert config.MAX_RETRIES_BROWSE == 2
    
    def test_max_retries_custom(self):
        """Test custom max retries value from environment"""
        custom_retries = "5"
        with patch.dict(os.environ, {'BROWSE_MAX_RETRIES': custom_retries}):
            config = DropshipProductFinderConfig()
            assert config.MAX_RETRIES_BROWSE == 5
    
    def test_backoff_base_default(self):
        """Test default backoff base value"""
        with patch.dict(os.environ, {}, clear=True):
            config = DropshipProductFinderConfig()
            assert config.BACKOFF_BASE_BROWSE == 1.5
    
    def test_backoff_base_custom(self):
        """Test custom backoff base value from environment"""
        custom_backoff = "2.0"
        with patch.dict(os.environ, {'BROWSE_BACKOFF_BASE': custom_backoff}):
            config = DropshipProductFinderConfig()
            assert config.BACKOFF_BASE_BROWSE == 2.0
    
    def test_ebay_client_id_default(self):
        """Test default eBay client ID value"""
        config = DropshipProductFinderConfig()
        assert config.EBAY_CLIENT_ID == ""
    
    def test_ebay_client_id_custom(self):
        """Test custom eBay client ID from environment"""
        client_id = "test_client_id_123"
        with patch.dict(os.environ, {'EBAY_CLIENT_ID': client_id}):
            config = DropshipProductFinderConfig()
            assert config.EBAY_CLIENT_ID == client_id
    
    def test_ebay_client_secret_default(self):
        """Test default eBay client secret value"""
        config = DropshipProductFinderConfig()
        assert config.EBAY_CLIENT_SECRET == ""
    
    def test_ebay_client_secret_custom(self):
        """Test custom eBay client secret from environment"""
        client_secret = "test_client_secret_456"
        with patch.dict(os.environ, {'EBAY_CLIENT_SECRET': client_secret}):
            config = DropshipProductFinderConfig()
            assert config.EBAY_CLIENT_SECRET == client_secret
    
    def test_ebay_marketplaces_default(self):
        """Test default eBay marketplaces value"""
        config = DropshipProductFinderConfig()
        assert config.EBAY_MARKETPLACES == "EBAY_US"
    
    def test_ebay_marketplaces_custom(self):
        """Test custom eBay marketplaces from environment"""
        marketplaces = "EBAY_US,EBAY_DE,EBAY_AU"
        with patch.dict(os.environ, {'EBAY_MARKETPLACES': marketplaces}):
            config = DropshipProductFinderConfig()
            assert config.EBAY_MARKETPLACES == marketplaces
    
    def test_use_mock_finders_default(self):
        """Test default mock finders setting"""
        with patch.dict(os.environ, {}, clear=True):
            config = DropshipProductFinderConfig()
            assert config.USE_MOCK_FINDERS == True
    
    def test_use_mock_finders_false(self):
        """Test mock finders set to false"""
        with patch.dict(os.environ, {'USE_MOCK_FINDERS': 'false'}):
            config = DropshipProductFinderConfig()
            assert config.USE_MOCK_FINDERS == False
    
    def test_use_mock_finders_true(self):
        """Test mock finders set to true"""
        with patch.dict(os.environ, {'USE_MOCK_FINDERS': 'true'}):
            config = DropshipProductFinderConfig()
            assert config.USE_MOCK_FINDERS == True