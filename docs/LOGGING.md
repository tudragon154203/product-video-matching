# Unified Logging Convention

## Overview

The product-video-matching project implements a unified logging system based on Python's standard `logging` module with enhancements for structured logging, correlation ID tracking, and consistent formatting across all services. This logging system provides:

- **Structured logging** with JSON format support
- **Correlation ID tracking** for request tracing across services
- **Consistent log levels** and formatting
- **Context-aware logging** with the `ContextLogger` wrapper
- **Environment-based configuration**

## Core Components

### ContextLogger

The `ContextLogger` is a thin wrapper around Python's standard logger that supports structured kwargs and avoids `TypeError` when passing unknown keyword arguments.

```python
from common_py.logging_config import configure_logging

# Initialize logger
logger = configure_logging("my-service")

# Basic logging
logger.info("Service started")

# Structured logging with extra fields
logger.info("Processing job", job_id="job123", status="started", user_id="user456")

# Error logging with exception info
try:
    result = risky_operation()
except Exception as e:
    logger.error("Operation failed", error=str(e), job_id="job123")
```

### JsonFormatter

The `JsonFormatter` produces structured JSON logs that include correlation IDs when available:

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "name": "main-api",
  "level": "INFO",
  "message": "Service started",
  "correlation_id": "job123"
}
```

## Configuration Options

### Basic Configuration

```python
from common_py.logging_config import configure_logging

# Basic configuration
logger = configure_logging("my-service")

# With custom log level
logger = configure_logging("my-service", log_level="DEBUG")

# With JSON format
logger = configure_logging("my-service", log_format="json")
```

### Environment Variables

Logging is configured through environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `LOG_FORMAT` | `text` | Log format (text or json) |

### Service-Specific Configuration

Each service can override the global logging configuration:

```python
# In service config_loader.py
from common_py.logging_config import configure_logging
from config import config

# Use global config or service-specific override
log_level = getattr(config, 'LOG_LEVEL', 'INFO')
logger = configure_logging("my-service", log_level=log_level)
```

## Correlation ID Usage

### Setting Correlation ID

Correlation IDs are used to trace requests across multiple services:

```python
from common_py.logging_config import set_correlation_id

# Set correlation ID for the current context
set_correlation_id("job123")

# All subsequent logs will include the correlation ID
logger.info("Processing request")
# Output: {"timestamp": "...", "name": "service", "level": "INFO", "message": "Processing request", "correlation_id": "job123"}
```

### Automatic Correlation ID from Events

When processing events from RabbitMQ, correlation IDs are automatically extracted and set:

```python
# In message handlers
async def handle_event(event_data):
    # Correlation ID is automatically set from the message
    logger.info("Processing event", event_type="match_request")
    # Log will include correlation_id from the original message
```

### Publishing Events with Correlation ID

When publishing events, always include the correlation ID:

```python
from common_py.messaging import MessageBroker

broker = MessageBroker(config.BUS_BROKER)

# Publish with correlation ID
await broker.publish_event(
    "match.request",
    {"job_id": "job123", "data": {...}},
    correlation_id="job123"  # Use the same correlation ID
)
```

## Structured Logging Examples

### Basic Logging

```python
# Simple message
logger.info("Service started")

# With structured data
logger.info("User login", user_id="user123", ip="192.168.1.1", success=True)
```

### Error Logging

```python
try:
    result = perform_operation()
except Exception as e:
    logger.error("Operation failed", 
                error=str(e),
                error_type=type(e).__name__,
                operation="data_processing",
                retry_count=3)
```

### Performance Logging

```python
import time

start_time = time.time()
# ... perform operation ...
duration = time.time() - start_time

logger.info("Operation completed",
            operation="database_query",
            duration_ms=round(duration * 1000, 2),
            rows_processed=150)
```

### Request/Response Logging

```python
logger.info("Received request",
            method="POST",
            endpoint="/api/match",
            content_type="application/json",
            payload_size=1024)

# ... process request ...

logger.info("Sent response",
            status_code=200,
            response_size=2048,
            processing_time_ms=150)
```

## Best Practices and Conventions

### 1. Logger Naming

Use the service name as the logger name:

```python
# In main.py
logger = configure_logging("main-api")

# In handlers
logger = configure_logging("main-api.handlers")
```

### 2. Log Levels

- **DEBUG**: Detailed information for debugging
- **INFO**: General information about service operation
- **WARNING**: Potentially harmful situations
- **ERROR**: Serious errors that prevent normal operation
- **CRITICAL**: Very serious errors that may cause service termination

```python
# Use appropriate log levels
logger.debug("Detailed debug info", variable=value)  # Only in development
logger.info("Service operation completed", operation="data_sync")
logger.warning("Potential issue detected", threshold=0.9, current=0.85)
logger.error("Service operation failed", error=str(e))
logger.critical("Service cannot continue", fatal_error=True)
```

### 3. Structured Data

Always use structured data instead of string formatting:

```python
# Good
logger.info("User login", user_id="user123", ip="192.168.1.1")

# Bad
logger.info(f"User {user_id} logged in from {ip}")
```

### 4. Error Handling

```python
try:
    result = risky_operation()
except Exception as e:
    logger.error("Operation failed",
                error=str(e),
                error_type=type(e).__name__,
                operation="critical_task",
                correlation_id=current_correlation_id)
    raise
```

### 5. Context Management

Use correlation IDs consistently across service boundaries:

```python
async def process_job(job_id: str):
    # Set correlation ID for the entire job processing
    set_correlation_id(job_id)
    
    logger.info("Starting job processing", job_id=job_id)
    
    try:
        # Process job steps
        await step1(job_id)
        await step2(job_id)
        
        logger.info("Job completed successfully", job_id=job_id)
    except Exception as e:
        logger.error("Job processing failed", job_id=job_id, error=str(e))
        raise
```

### 6. Performance Considerations

- Avoid expensive operations in log statements
- Use lazy evaluation for complex data:
```python
# Good
logger.debug("Complex data", data=expensive_to_compute())

# Bad
logger.debug(f"Complex data: {expensive_to_compute()}")
```

## Migration Guide

### For Existing Services

1. **Replace standard logger imports**:
```python
# Old
import logging
logger = logging.getLogger(__name__)

# New
from common_py.logging_config import configure_logging
logger = configure_logging(__name__)
```

2. **Update log calls to use structured format**:
```python
# Old
logger.info(f"Processing job {job_id} for user {user_id}")

# New
logger.info("Processing job", job_id=job_id, user_id=user_id)
```

3. **Add correlation ID support**:
```python
# In request handlers
from common_py.logging_config import set_correlation_id

async def handle_request(request):
    correlation_id = request.headers.get("X-Correlation-ID")
    set_correlation_id(correlation_id)
    
    logger.info("Processing request", method=request.method, path=request.url.path)
```

### For New Services

1. **Initialize logger in main.py**:
```python
from common_py.logging_config import configure_logging

logger = configure_logging("my-service")
```

2. **Use structured logging throughout**:
```python
logger.info("Service started", version="1.0.0")
logger.info("Processing request", endpoint="/api/data", method="POST")
```

3. **Implement correlation ID propagation**:
```python
# When calling other services
await other_service.process(data, correlation_id=correlation_id)
```

## Environment Variables and Configuration

### Global Configuration (`.env`)

```bash
# infra/pvm/.env
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Service-Specific Configuration

```bash
# services/my-service/.env
# Service-specific logging overrides
LOG_LEVEL=DEBUG
```

### Docker Compose Configuration

```yaml
# infra/pvm/docker-compose.dev.yml
services:
  main-api:
    environment:
      - LOG_LEVEL=INFO
      - LOG_FORMAT=json
  matcher:
    environment:
      - LOG_LEVEL=DEBUG
      - LOG_FORMAT=json
```

### Development vs Production

**Development** (`LOG_LEVEL=DEBUG`):
- Detailed debugging information
- Performance timing logs
- Verbose request/response logging

**Production** (`LOG_LEVEL=INFO`):
- Business operation logs
- Error and exception logs
- Performance metrics
- Security audit logs

## Log Aggregation and Monitoring

### Structured Log Fields

All logs include these standard fields:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string | ISO 8601 timestamp |
| `name` | string | Logger name (service name) |
| `level` | string | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `message` | string | Log message |
| `correlation_id` | string | Request correlation ID (when available) |
| `extra_kwargs` | object | Additional structured data |

### Example Log Analysis

```bash
# Filter logs by correlation ID
grep "correlation_id.*job123" logs/*.json

# Count errors by service
jq -r 'select(.level == "ERROR") | .name' logs/*.json | sort | uniq -c

# Track request flow across services
grep "correlation_id.*job123" logs/*.json | jq -r '[.timestamp, .name, .message] | @tsv'
```

## Troubleshooting

### Common Issues

1. **Logs not showing correlation IDs**:
   - Ensure `set_correlation_id()` is called before logging
   - Check that correlation ID is properly propagated between services

2. **JSON format not working**:
   - Verify `LOG_FORMAT=json` is set
   - Check that the JsonFormatter is being used

3. **Duplicate log messages**:
   - Ensure `base.propagate = False` is set in `configure_logging`
   - Check for multiple handlers on the same logger

### Debug Logging

Enable debug logging for troubleshooting:

```bash
# Set environment variable
export LOG_LEVEL=DEBUG

# Or in Docker Compose
environment:
  - LOG_LEVEL=DEBUG
```

### Performance Impact

- JSON logging has minimal performance overhead
- Debug logging should be disabled in production
- Use appropriate log levels to reduce I/O

## Integration with External Systems

### ELK Stack Integration

Logs can be easily integrated with ELK (Elasticsearch, Logstash, Kibana) stack:

```json
{
  "@timestamp": "2024-01-15T10:30:00.123Z",
  "service": "main-api",
  "level": "INFO",
  "message": "Service started",
  "correlation_id": "job123",
  "extra": {
    "job_id": "job123",
    "user_id": "user456"
  }
}
```

### Prometheus Integration

Log metrics can be exported to Prometheus:

```python
from common_py.metrics import Metrics

metrics = Metrics()
metrics.counter("log_messages_total", "Total log messages", ["level", "service"])
```

This unified logging system provides consistent, traceable, and structured logging across all services in the product-video-matching ecosystem.