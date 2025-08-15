---
inclusion: fileMatch
fileMatchPattern: '*api*|*handler*|*endpoint*'
---

# API Design Guidelines

## REST API Standards
- **Framework**: Use FastAPI for all REST APIs
- **Documentation**: Auto-generate OpenAPI specs at `/docs`
- **Versioning**: Include version in URL path (`/v1/...`)
- **Content-Type**: Use `application/json` for all requests/responses

## Response Format
**Success Response:**
```json
{
  "status": "success",
  "data": { ... }
}
```

**Error Response:**
```json
{
  "status": "error", 
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": { ... }
  }
}
```

## Main API Endpoints
- `POST /start-job` - Start matching job
- `GET /status/{job_id}` - Get job status and progress
- `GET /health` - Service health check

## Results API Endpoints
- `GET /results` - List matches with filtering
- `GET /products/{id}` - Product details
- `GET /videos/{id}` - Video details  
- `GET /matches/{id}` - Match details
- `GET /evidence/{match_id}` - Evidence image
- `GET /stats` - System statistics

## Request Validation
- **Pydantic Models**: Use for request/response validation
- **Type Hints**: Required for all endpoint parameters
- **Error Handling**: Return 422 for validation errors
- **Input Sanitization**: Validate and sanitize all inputs

## Pagination & Filtering
- **Query Parameters**: `limit`, `offset` for pagination
- **Filtering**: Support common filters (`min_score`, `industry`, `job_id`)
- **Response Headers**: Include `X-Total-Count`, `X-Limit`, `X-Offset`
- **Default Limits**: 100 items max, reasonable defaults

## Error Handling
- **HTTP Status Codes**: Use appropriate codes (200, 400, 404, 422, 500)
- **Error Codes**: Consistent error code naming
- **Logging**: Log all errors with context
- **User-Friendly**: Provide clear error messages

## Security Considerations
- **Input Validation**: Validate all inputs thoroughly
- **Rate Limiting**: Implement for production (not in MVP)
- **CORS**: Configure appropriately for frontend access
- **Authentication**: Design for future implementation

## Performance
- **Async Handlers**: Use async/await for I/O operations
- **Database Queries**: Optimize with proper indexes
- **Caching**: Cache frequently accessed data
- **Timeouts**: Set reasonable request timeouts