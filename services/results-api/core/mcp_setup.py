"""
MCP (Model Context Protocol) server setup and integration module.
Provides FastAPI MCP server configuration and mounting functionality.
"""
from typing import Optional
import logging

from fastapi import FastAPI

from core.config import MCPSettings
from core.exceptions import MCPError

logger = logging.getLogger(__name__)


def setup_mcp_server(app: FastAPI, settings: MCPSettings) -> None:
    """
    Setup and mount MCP server to the FastAPI application.
    
    Args:
        app: FastAPI application instance
        settings: MCP configuration settings
        
    Raises:
        MCPError: If MCP server setup fails
    """
    if not settings.enabled:
        logger.info("MCP server is disabled")
        return
    
    try:
        # Import fastapi_mcp library
        try:
            from fastapi_mcp import FastAPIMCP
        except ImportError as e:
            logger.error("fastapi_mcp library not found. Install with: pip install fastapi-mcp")
            raise MCPError("fastapi_mcp library not installed") from e
        
        # Create MCP server that exposes FastAPI endpoints as tools
        mcp_server = FastAPIMCP(
            app=app,
            title=settings.title,
            description=settings.description
        )
        
        # Mount the MCP server to the main app
        app.mount(settings.mount_path, mcp_server.get_asgi_app())
        
        logger.info(
            f"MCP server mounted successfully at {settings.mount_path}",
            extra={
                "mount_path": settings.mount_path,
                "title": settings.title,
                "description": settings.description
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to setup MCP server: {e}")
        raise MCPError(f"Failed to setup MCP server: {e}") from e


def create_mcp_server_standalone(settings: MCPSettings) -> Optional[FastAPI]:
    """
    Create a standalone MCP server application.
    
    Args:
        settings: MCP configuration settings
        
    Returns:
        FastAPI application instance or None if disabled
        
    Raises:
        MCPError: If MCP server creation fails
    """
    if not settings.enabled:
        logger.info("MCP server is disabled")
        return None
    
    try:
        # Import fastapi_mcp library
        try:
            from fastapi_mcp import FastAPIMCP
        except ImportError as e:
            logger.error("fastapi_mcp library not found. Install with: pip install fastapi-mcp")
            raise MCPError("fastapi_mcp library not installed") from e
        
        # Create standalone MCP server
        mcp_app = FastAPI(
            title=settings.title,
            description=settings.description,
            version="1.0.0"
        )
        
        # Note: For standalone server, you would need to manually register tools
        # This is a placeholder for future implementation if needed
        logger.info(
            "Standalone MCP server created",
            extra={
                "title": settings.title,
                "description": settings.description
            }
        )
        
        return mcp_app
        
    except Exception as e:
        logger.error(f"Failed to create standalone MCP server: {e}")
        raise MCPError(f"Failed to create standalone MCP server: {e}") from e


def validate_mcp_configuration(settings: MCPSettings) -> bool:
    """
    Validate MCP server configuration.
    
    Args:
        settings: MCP configuration settings
        
    Returns:
        True if configuration is valid
        
    Raises:
        MCPError: If configuration is invalid
    """
    try:
        # Validate mount path
        if not settings.mount_path.startswith('/'):
            raise MCPError("MCP mount path must start with '/'")
        
        # Validate title and description
        if not settings.title.strip():
            raise MCPError("MCP server title cannot be empty")
        
        if not settings.description.strip():
            raise MCPError("MCP server description cannot be empty")
        
        logger.info("MCP configuration validation passed")
        return True
        
    except Exception as e:
        logger.error(f"MCP configuration validation failed: {e}")
        raise MCPError(f"Invalid MCP configuration: {e}") from e


def get_mcp_tools_info(app: FastAPI) -> dict:
    """
    Get information about available MCP tools from the FastAPI app.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        Dictionary containing MCP tools information
    """
    tools_info = {
        "total_routes": len(app.routes),
        "api_routes": [],
        "mcp_enabled": True
    }
    
    # Extract route information
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            tools_info["api_routes"].append({
                "path": route.path,
                "methods": list(route.methods) if route.methods else [],
                "name": getattr(route, 'name', 'unnamed')
            })
    
    return tools_info