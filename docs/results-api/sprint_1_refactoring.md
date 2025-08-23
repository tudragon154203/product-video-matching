UPDATED DETAILED REFACTORING PLAN (DEPENDENCIES IN CORE)


REFACTORED STRUCTURE PLAN:
plaintext

services/results-api/
├── main.py (clean FastAPI app initialization + MCP server mounting)
├── api/
│   ├── __init__.py
│   └── endpoints.py (endpoint definitions)
├── core/
│   ├── __init__.py
│   ├── config.py (Pydantic settings)
│   ├── exceptions.py (custom exceptions & handlers)
│   └── mcp_setup.py (MCP server configuration and mounting)
├── services/
│   ├── __init__.py
│   └── results_service.py (relocated from service.py)
├── schemas/
│   ├── __init__.py
│   ├── entities.py
│   ├── requests.py
│   └── responses.py (already exists)
└── tests/

MCP SERVER INTEGRATION:
The FastAPI MCP server must be mounted to the main app instance to provide enhanced tooling capabilities:

1. **MCP Setup Module** (core/mcp_setup.py):
   - Configure MCP server with appropriate tools
   - Handle MCP server lifecycle management
   - Provide integration with existing FastAPI routes

2. **Main App Integration** (main.py):
   - Mount MCP server as a sub-application
   - Ensure proper startup/shutdown handling
   - Maintain compatibility with existing API endpoints

3. **Configuration Support**:
   - Add MCP-specific settings to core/config.py
   - Environment variables for MCP server configuration
   - Optional MCP server enabling/disabling

CORRECTIONS TO PLAN:



IMPLEMENTATION SEQUENCE:
✅ Create configuration management (core/config.py)
✅ Create custom exceptions (core/exceptions.py)
✅ Create dependencies (core/dependencies.py - already created but needs move)
Create API endpoint structure (api/endpoints.py)
Update main application file
Mount FastAPI MCP server to the app instance
Refactor service layer
Update requirements
Test the refactored service

EXPECTED IMPROVEMENTS:
Better organization: Core components together (config, exceptions, dependencies)
Dependency injection: Proper database session management
Global error handling: Consistent error responses with correlation IDs
Configuration management: Environment-based settings with validation
Modular endpoint structure: Clean API separation from core logic
MCP Integration: FastAPI MCP server mounted for enhanced tooling capabilities
