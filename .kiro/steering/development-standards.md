---
inclusion: always
---

# Development Standards

## Code Style & Quality
- **Python**: Follow PEP 8 standards
- **Type Hints**: Required for all public functions and methods
- **Docstrings**: Use Google-style docstrings for public APIs
- **Logging**: Use structured JSON logging with appropriate levels
- **Error Handling**: Implement proper exception handling with meaningful messages

## Service Development Patterns
- **FastAPI**: Use for REST APIs with automatic OpenAPI documentation
- **Async/Await**: Use asyncio for I/O operations and event handling
- **Dependency Injection**: Use FastAPI's dependency system
- **Health Checks**: Implement `/health` endpoint for all services
- **Graceful Shutdown**: Handle SIGTERM for clean service shutdown

## Event-Driven Patterns
- **Event Validation**: Validate all events against JSON schemas in `libs/contracts`
- **Idempotency**: Design event handlers to be idempotent
- **Error Handling**: Use dead letter queues for failed message processing
- **Tracing**: Include `job_id` and `parent_event_id` for request tracing

## Database Patterns
- **Migrations**: Use Alembic for database schema changes
- **Connection Pooling**: Use SQLAlchemy with proper connection management
- **Transactions**: Use database transactions for consistency
- **Indexes**: Add appropriate indexes for query performance

## Testing Standards
- **Unit Tests**: Focus on business logic and core algorithms
- **Integration Tests**: Test service interactions and database operations
- **Minimal Coverage**: Prioritize critical paths over 100% coverage
- **Mock External APIs**: Use mocks for Amazon, eBay, YouTube APIs

## Docker & Infrastructure
- **Multi-stage Builds**: Use for production optimization
- **Health Checks**: Include Docker health checks for all services
- **Volume Mounts**: Use for development with live code reloading
- **Environment Variables**: Use `.env` files for configuration