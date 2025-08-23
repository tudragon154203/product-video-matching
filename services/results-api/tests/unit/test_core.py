"""
Unit tests for core components (config, exceptions, dependencies).
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import Request
from fastapi.exceptions import RequestValidationError

from core.config import (
    DatabaseSettings, 
    AppSettings, 
    MCPSettings, 
    Settings, 
    get_settings, 
    reset_settings
)
from core.exceptions import (
    BaseAPIException,
    ResourceNotFound,
    ValidationError,
    DatabaseError,
    MCPError,
    ServiceError,
    ExceptionHandlers
)
from core.dependencies import (
    DatabaseManagerSingleton,
    get_db_session,
    get_results_service,
    startup_dependencies,
    shutdown_dependencies
)


class TestDatabaseSettings:
    """Test database settings configuration"""
    
    def test_default_values(self):
        """Test default database settings"""
        settings = DatabaseSettings()
        assert settings.pool_size == 5
        assert settings.max_overflow == 10
        assert settings.timeout == 30
    
    def test_dsn_validation(self):
        """Test DSN validation"""
        # Valid DSN
        settings = DatabaseSettings(dsn="postgresql://user:pass@localhost:5432/db")
        assert str(settings.dsn).startswith("postgresql://")
        
        # Invalid DSN should raise validation error
        with pytest.raises(ValueError):
            DatabaseSettings(dsn="invalid-dsn")


class TestAppSettings:
    """Test application settings configuration"""
    
    def test_default_values(self):
        """Test default application settings"""
        settings = AppSettings()
        assert settings.title == "Results API"
        assert settings.version == "1.0.0"
        assert settings.debug is False
        assert settings.log_level == "INFO"
    
    def test_cors_origins_validation(self):
        """Test CORS origins validation"""
        settings = AppSettings(cors_origins="http://localhost:3000,http://localhost:8080")
        assert isinstance(settings.cors_origins, list)
        assert len(settings.cors_origins) == 2
    
    def test_log_level_validation(self):
        """Test log level validation"""
        settings = AppSettings(log_level="DEBUG")
        assert settings.log_level == "DEBUG"
        
        with pytest.raises(ValueError):
            AppSettings(log_level="INVALID")


class TestMCPSettings:
    """Test MCP settings configuration"""
    
    def test_default_values(self):
        """Test default MCP settings"""
        settings = MCPSettings()
        assert settings.enabled is True
        assert settings.title == "Results API MCP Server"
        assert settings.mount_path == "/mcp"
    
    def test_mount_path_validation(self):
        """Test mount path validation"""
        settings = MCPSettings(mount_path="mcp")
        assert settings.mount_path == "/mcp"
        
        settings = MCPSettings(mount_path="/custom-mcp")
        assert settings.mount_path == "/custom-mcp"


class TestSettings:
    """Test main settings configuration"""
    
    def test_settings_initialization(self):
        """Test settings initialization"""
        settings = Settings()
        assert isinstance(settings.database, DatabaseSettings)
        assert isinstance(settings.app, AppSettings)
        assert isinstance(settings.mcp, MCPSettings)
    
    def test_get_settings_singleton(self):
        """Test settings singleton behavior"""
        reset_settings()
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2


class TestBaseAPIException:
    """Test base API exception"""
    
    def test_exception_creation(self):
        """Test exception creation with all parameters"""
        exc = BaseAPIException(
            message="Test error",
            error_code="TEST_ERROR",
            status_code=400,
            details=[{"field": "test", "message": "error"}]
        )
        
        assert exc.message == "Test error"
        assert exc.error_code == "TEST_ERROR"
        assert exc.status_code == 400
        assert len(exc.details) == 1
        assert exc.correlation_id is not None
    
    def test_to_dict(self):
        """Test exception to dictionary conversion"""
        exc = BaseAPIException("Test error", "TEST_ERROR", 400)
        result = exc.to_dict()
        
        assert result["message"] == "Test error"
        assert result["error_code"] == "TEST_ERROR"
        assert "correlation_id" in result
        assert "timestamp" in result
        assert "details" in result


class TestSpecificExceptions:
    """Test specific exception classes"""
    
    def test_resource_not_found(self):
        """Test ResourceNotFound exception"""
        exc = ResourceNotFound("Product", "123")
        assert exc.status_code == 404
        assert exc.error_code == "RESOURCE_NOT_FOUND"
        assert "Product with id '123' not found" in exc.message
    
    def test_validation_error(self):
        """Test ValidationError exception"""
        exc = ValidationError("email", "Invalid format")
        assert exc.status_code == 422
        assert exc.error_code == "VALIDATION_ERROR"
        assert "email" in exc.message
    
    def test_database_error(self):
        """Test DatabaseError exception"""
        exc = DatabaseError("Connection failed")
        assert exc.status_code == 500
        assert exc.error_code == "DATABASE_ERROR"
        assert exc.message == "Connection failed"
    
    def test_mcp_error(self):
        """Test MCPError exception"""
        exc = MCPError("MCP setup failed")
        assert exc.status_code == 500
        assert exc.error_code == "MCP_ERROR"
        assert exc.message == "MCP setup failed"
    
    def test_service_error(self):
        """Test ServiceError exception"""
        exc = ServiceError("Service unavailable")
        assert exc.status_code == 500
        assert exc.error_code == "SERVICE_ERROR"
        assert exc.message == "Service unavailable"


class TestExceptionHandlers:
    """Test exception handlers"""
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock request"""
        request = MagicMock()
        request.url.path = "/test"
        request.method = "GET"
        return request
    
    @pytest.mark.asyncio
    async def test_api_exception_handler(self, mock_request):
        """Test API exception handler"""
        exc = BaseAPIException("Test error", "TEST_ERROR", 400)
        
        with patch('core.exceptions.logger') as mock_logger:
            response = await ExceptionHandlers.api_exception_handler(mock_request, exc)
            
            assert response.status_code == 400
            mock_logger.error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validation_exception_handler(self, mock_request):
        """Test validation exception handler"""
        # Create a mock validation error
        validation_error = RequestValidationError([
            {
                "loc": ("body", "email"),
                "msg": "field required",
                "type": "value_error.missing"
            }
        ])
        
        with patch('core.exceptions.logger') as mock_logger:
            response = await ExceptionHandlers.validation_exception_handler(
                mock_request, validation_error
            )
            
            assert response.status_code == 422
            mock_logger.warning.assert_called_once()


class TestDatabaseManagerSingleton:
    """Test database manager singleton"""
    
    @pytest.mark.asyncio
    async def test_get_instance(self):
        """Test getting database manager instance"""
        with patch('core.dependencies.DatabaseManager') as mock_db_class:
            mock_db = AsyncMock()
            mock_db_class.return_value = mock_db
            
            # Reset singleton
            DatabaseManagerSingleton._instance = None
            DatabaseManagerSingleton._connected = False
            
            instance = await DatabaseManagerSingleton.get_instance()
            
            assert instance is mock_db
            mock_db.connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_connection(self):
        """Test closing database connection"""
        with patch('core.dependencies.DatabaseManager') as mock_db_class:
            mock_db = AsyncMock()
            mock_db_class.return_value = mock_db
            
            # Set up singleton state
            DatabaseManagerSingleton._instance = mock_db
            DatabaseManagerSingleton._connected = True
            
            await DatabaseManagerSingleton.close_connection()
            
            mock_db.disconnect.assert_called_once()
            assert DatabaseManagerSingleton._connected is False


class TestDependencyFunctions:
    """Test dependency injection functions"""
    
    @pytest.mark.asyncio
    async def test_get_db_session(self):
        """Test get_db_session dependency"""
        with patch.object(DatabaseManagerSingleton, 'get_instance') as mock_get_instance:
            mock_db = AsyncMock()
            mock_get_instance.return_value = mock_db
            
            result = await get_db_session()
            
            assert result is mock_db
            mock_get_instance.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_results_service(self):
        """Test get_results_service dependency"""
        mock_db = AsyncMock()
        
        with patch('services.results_service.ResultsService') as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            
            result = await get_results_service(mock_db)
            
            assert result is mock_service
            mock_service_class.assert_called_once_with(mock_db)
    
    @pytest.mark.asyncio
    async def test_startup_dependencies(self):
        """Test startup dependencies"""
        with patch.object(DatabaseManagerSingleton, 'get_instance') as mock_get_instance:
            mock_db = AsyncMock()
            mock_get_instance.return_value = mock_db
            
            await startup_dependencies()
            
            mock_get_instance.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_shutdown_dependencies(self):
        """Test shutdown dependencies"""
        with patch.object(DatabaseManagerSingleton, 'close_connection') as mock_close:
            await shutdown_dependencies()
            mock_close.assert_called_once()