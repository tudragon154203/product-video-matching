# API Documentation

This document provides detailed API documentation for the Product-Video Matching System.
## Updated Service Names

The following services have been renamed as part of our latest update:
- **Catalog Collector** → **Dropship Product Finder**
- **Media Ingestion** → **Video Crawler**

All API endpoints and functionality remain unchanged.

## Base URLs

- **Main API**: `http://localhost:8000`


## Authentication

Currently, no authentication is required for MVP. In production, implement appropriate authentication mechanisms.

## Common Response Formats

### Success Response
```json
{
  "status": "success",
  "data": { ... }
}
```

### Error Response
```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": { ... }
  }
}
```

## Main API

### Start Job

Start a new product-video matching job.

**Endpoint:** `POST /start-job`

**Request Body:**
```json
{
  "industry": "ergonomic pillows",
  "top_amz": 10,
  "top_ebay": 5,
  "queries": ["ergonomic pillows", "neck support pillows"],
  "platforms": ["youtube"],
  "recency_days": 365
}
```

**Parameters:**
- `industry` (string, required): Industry keyword for search
- `top_amz` (integer, optional, default: 10): Number of Amazon products to collect
- `top_ebay` (integer, optional, default: 5): Number of eBay products to collect
- `queries` (array, optional): Custom search queries (defaults to industry keyword)
- `platforms` (array, optional, default: ["youtube"]): Video platforms to search
- `recency_days` (integer, optional, default: 365): How many days back to search videos

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "started"
}
```

**Status Codes:**
- `200`: Job started successfully
- `400`: Invalid request parameters
- `500`: Internal server error

### Get Job Status

Get the current status and progress of a job.

**Endpoint:** `GET /status/{job_id}`

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "phase": "matching",
  "percent": 75.0,
  "counts": {
    "products": 15,
    "videos": 8,
    "matches": 3
  }
}
```

**Phases:**
- `collection`: Collecting products and videos
- `feature_extraction`: Extracting visual features
- `matching`: Performing similarity matching
- `evidence`: Generating evidence images
- `completed`: Job finished successfully
- `failed`: Job failed with errors

**Status Codes:**
- `200`: Status retrieved successfully
- `404`: Job not found
- `500`: Internal server error

### Health Check

Check main API service health.

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "service": "main-api",
  "ollama": "healthy",
  "database": "healthy",
  "broker": "healthy"
}
```

### Get Job Images

Get images for a specific job with filtering and pagination.

**Endpoint:** `GET /jobs/{job_id}/images`

**Query Parameters:**
- `job_id` (string, required): The job ID to filter images by
- `product_id` (string, optional): Filter by product ID
- `q` (string, optional): Search query for product titles and image IDs (case-insensitive)
- `limit` (integer, optional, default: 100): Maximum number of items to return (1-1000)
- `offset` (integer, optional, default: 0): Number of items to skip for pagination
- `sort_by` (string, optional, default: `updated_at`, pattern: `^(img_id|updated_at)$`): Field to sort by
- `order` (string, optional, default: `DESC`, pattern: `^(ASC|DESC)$`): Sort order

**Response:**
```json
{
  "items": [
    {
      "img_id": "img-123",
      "product_id": "prod-456",
      "local_path": "/app/data/images/img-123.jpg",
      "product_title": "Example Product Title",
      "updated_at": "2024-01-15T10:30:00+07:00"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

**Status Codes:**
- `200`: Images retrieved successfully
- `404`: Job not found
- `500`: Internal server error

### Get Job Videos

Get videos for a specific job with filtering and pagination.

**Endpoint:** `GET /jobs/{job_id}/videos`

**Query Parameters:**
- `job_id` (string, required): The job ID to filter videos by
- `q` (string, optional): Search query for video titles (case-insensitive)
- `platform` (string, optional): Filter by platform (e.g., 'youtube', 'tiktok')
- `min_frames` (integer, optional): Minimum number of frames a video must have
- `limit` (integer, optional, default: 100): Maximum number of items to return (1-1000)
- `offset` (integer, optional, default: 0): Number of items to skip for pagination
- `sort_by` (string, optional, default: `updated_at`, pattern: `^(updated_at|duration_s|frames_count|title)$`): Field to sort by
- `order` (string, optional, default: `DESC`, pattern: `^(ASC|DESC)$`): Sort order

**Response:**
```json
{
  "items": [
    {
      "video_id": "vid-123",
      "platform": "youtube",
      "url": "https://www.youtube.com/watch?v=example",
      "title": "Example Video Title",
      "duration_s": 120.5,
      "frames_count": 240,
      "updated_at": "2024-01-15T10:30:00+07:00"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

**Status Codes:**
- `200`: Videos retrieved successfully
- `404`: Job not found
- `500`: Internal server error

### Get Video Frames

Get frames for a specific video with pagination and sorting.

**Endpoint:** `GET /jobs/{job_id}/videos/{video_id}/frames`

**Path Parameters:**
- `job_id` (string, required): The job ID (used for validation)
- `video_id` (string, required): The video ID to get frames for

**Query Parameters:**
- `limit` (integer, optional, default: 100): Maximum number of items to return (1-1000)
- `offset` (integer, optional, default: 0): Number of items to skip for pagination
- `sort_by` (string, optional, default: `ts`, pattern: `^(ts|frame_id)$`): Field to sort by
- `order` (string, optional, default: `ASC`, pattern: `^(ASC|DESC)$`): Sort order

**Response:**
```json
{
  "items": [
    {
      "frame_id": "frame-123",
      "ts": 10.5,
      "local_path": "/app/data/frames/frame-123.jpg",
      "updated_at": "2024-01-15T10:30:00+07:00"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

**Status Codes:**
- `200`: Frames retrieved successfully
- `404`: Job or video not found
- `500`: Internal server error

### Get Features Summary

Get features summary for a job including counts and progress for product images and video frames.

**Endpoint:** `GET /jobs/{job_id}/features/summary`

**Path Parameters:**
- `job_id` (string, required): The job ID

**Response:**
```json
{
  "job_id": "job-123",
  "product_images": {
    "total": 10,
    "segment": { "done": 8, "percent": 80.0 },
    "embedding": { "done": 9, "percent": 90.0 },
    "keypoints": { "done": 7, "percent": 70.0 }
  },
  "video_frames": {
    "total": 20,
    "segment": { "done": 15, "percent": 75.0 },
    "embedding": { "done": 18, "percent": 90.0 },
    "keypoints": { "done": 12, "percent": 60.0 }
  },
  "updated_at": "2024-01-15T10:30:00+07:00"
}
```

**Status Codes:**
- `200`: Summary retrieved successfully
- `404`: Job not found
- `500`: Internal server error

### Get Product Images Features

Get product images features for a job with filtering and pagination.

**Endpoint:** `GET /jobs/{job_id}/features/product-images`

**Path Parameters:**
- `job_id` (string, required): The job ID

**Query Parameters:**
- `has` (string, optional, default: `any`, pattern: `^(segment|embedding|keypoints|none|any)$`): Filter by feature presence
- `limit` (integer, optional, default: 100): Maximum number of items to return (1-1000)
- `offset` (integer, optional, default: 0): Number of items to skip for pagination
- `sort_by` (string, optional, default: `updated_at`, pattern: `^(updated_at|img_id)$`): Field to sort by
- `order` (string, optional, default: `DESC`, pattern: `^(ASC|DESC)$`): Sort order

**Response:**
```json
{
  "items": [
    {
      "img_id": "img-123",
      "product_id": "prod-456",
      "has_segment": true,
      "has_embedding": true,
      "has_keypoints": false,
      "paths": {
        "segment": "/app/data/masked/img-123.jpg",
        "embedding": null,
        "keypoints": null
      },
      "updated_at": "2024-01-15T10:30:00+07:00"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

**Status Codes:**
- `200`: Features retrieved successfully
- `404`: Job not found
- `500`: Internal server error

### Get Video Frames Features

Get video frames features for a job with filtering and pagination.

**Endpoint:** `GET /jobs/{job_id}/features/video-frames`

**Path Parameters:**
- `job_id` (string, required): The job ID

**Query Parameters:**
- `video_id` (string, optional): Filter by video ID
- `has` (string, optional, default: `any`, pattern: `^(segment|embedding|keypoints|none|any)$`): Filter by feature presence
- `limit` (integer, optional, default: 100): Maximum number of items to return (1-1000)
- `offset` (integer, optional, default: 0): Number of items to skip for pagination
- `sort_by` (string, optional, default: `updated_at`, pattern: `^(updated_at|frame_id|ts)$`): Field to sort by
- `order` (string, optional, default: `DESC`, pattern: `^(ASC|DESC)$`): Sort order

**Response:**
```json
{
  "items": [
    {
      "frame_id": "frame-123",
      "video_id": "vid-456",
      "ts": 10.5,
      "has_segment": true,
      "has_embedding": true,
      "has_keypoints": false,
      "paths": {
        "segment": "/app/data/masked/frame-123.jpg",
        "embedding": null,
        "keypoints": null
      },
      "updated_at": "2024-01-15T10:30:00+07:00"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

**Status Codes:**
- `200`: Features retrieved successfully
- `404`: Job not found
- `500`: Internal server error

### Get Product Image Feature by ID

Get a single product image feature by ID.

**Endpoint:** `GET /features/product-images/{img_id}`

**Path Parameters:**
- `img_id` (string, required): The image ID

**Response:**
```json
{
  "img_id": "img-123",
  "product_id": "prod-456",
  "has_segment": true,
  "has_embedding": true,
  "has_keypoints": false,
  "paths": {
    "segment": "/app/data/masked/img-123.jpg",
    "embedding": null,
    "keypoints": null
  },
  "updated_at": "2024-01-15T10:30:00+07:00"
}
```

**Status Codes:**
- `200`: Feature retrieved successfully
- `404`: Product image not found
- `500`: Internal server error

### Get Video Frame Feature by ID

Get a single video frame feature by ID.

**Endpoint:** `GET /features/video-frames/{frame_id}`

**Path Parameters:**
- `frame_id` (string, required): The frame ID

**Response:**
```json
{
  "frame_id": "frame-123",
  "video_id": "vid-456",
  "ts": 10.5,
  "has_segment": true,
  "has_embedding": true,
  "has_keypoints": false,
  "paths": {
    "segment": "/app/data/masked/frame-123.jpg",
    "embedding": null,
    "keypoints": null
  },
  "updated_at": "2024-01-15T10:30:00+07:00"
}
```

**Status Codes:**
- `200`: Feature retrieved successfully
- `404`: Video frame not found
- `500`: Internal server error




## Configuration Parameters

### Port Configuration
- Main API: `http://localhost:8000`

- PostgreSQL UI: `http://localhost:8081`

### Database Configuration
- `POSTGRES_USER`: PostgreSQL username (default: postgres)
- `POSTGRES_PASSWORD`: PostgreSQL password (default: dev)
- `POSTGRES_DB`: PostgreSQL database name (default: product_video_matching)
- `POSTGRES_HOST`: PostgreSQL host (default: localhost)

### Message Broker Configuration
- `BUS_BROKER`: Message broker connection string (default: amqp://guest:guest@localhost:5672/)

### Data Storage
- `DATA_ROOT`: Root directory for data storage (default: ./data)

### Vision Models
- `EMBED_MODEL`: Vision embedding model (default: clip-vit-b32)

### Vector Search Configuration
- `RETRIEVAL_TOPK`: Number of results to return in vector search via PostgreSQL + pgvector (default: 20)

### Matching Thresholds
- `SIM_DEEP_MIN`: Minimum similarity threshold for deep matching (default: 0.82)
- `INLIERS_MIN`: Minimum inliers ratio for keypoint matching (default: 0.35)
- `MATCH_BEST_MIN`: Minimum score for best match (default: 0.88)
- `MATCH_CONS_MIN`: Minimum consistent matches (default: 2)
- `MATCH_ACCEPT`: Minimum acceptance score for matches (default: 0.80)

### Logging
- `LOG_LEVEL`: Logging level (default: INFO)

## Error Codes

### Common Error Codes

- `VALIDATION_ERROR`: Request validation failed
- `NOT_FOUND`: Requested resource not found
- `INTERNAL_ERROR`: Internal server error
- `DATABASE_ERROR`: Database operation failed
- `TIMEOUT_ERROR`: Operation timed out

### HTTP Status Codes

- `200`: Success
- `201`: Created
- `400`: Bad Request
- `404`: Not Found
- `422`: Unprocessable Entity
- `500`: Internal Server Error
- `503`: Service Unavailable

## Rate Limiting

Currently no rate limiting is implemented in MVP. For production:

- Implement rate limiting per IP/API key
- Typical limits: 100 requests/minute for job creation, 1000 requests/minute for queries
- Return `429 Too Many Requests` when limits exceeded

## Pagination

For endpoints that return lists (e.g., `/results`):

**Request Parameters:**
- `limit`: Maximum number of items (default: 100, max: 1000)
- `offset`: Number of items to skip (default: 0)

**Response Headers:**
- `X-Total-Count`: Total number of items available
- `X-Limit`: Applied limit
- `X-Offset`: Applied offset

## Filtering and Sorting

### Results Filtering

The `/results` endpoint supports various filters:

```bash
# Filter by minimum score
GET /results?min_score=0.8

# Filter by industry
GET /results?industry=pillows

# Filter by job
GET /results?job_id=550e8400-e29b-41d4-a716-446655440000

# Combine filters
GET /results?min_score=0.8&industry=pillows&limit=50
```

### Sorting

Results are sorted by:
- Default: `score DESC, created_at DESC`
- Products: `created_at DESC`
- Videos: `created_at DESC`

### WebSocket API (Future)

For real-time job progress updates (not implemented in MVP):

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/job/{job_id}');

// Receive progress updates
ws.onmessage = function(event) {
  const update = JSON.parse(event.data);
  console.log('Job progress:', update.percent);
};
```

## SDK Examples

### Python SDK Example

```python
import requests
import json

class ProductVideoMatchingClient:
    def __init__(self):
        self.base_url = "http://localhost:8000"
    
    def start_job(self, industry, top_amz=10, top_ebay=5):
        response = requests.post(f"{self.base_url}/start-job", json={
            "industry": industry,
            "top_amz": top_amz,
            "top_ebay": top_ebay,
            "platforms": ["youtube"]
        })
        return response.json()
    
    def get_job_status(self, job_id):
        response = requests.get(f"{self.base_url}/status/{job_id}")
        return response.json()
    
    def get_results(self, min_score=0.8, limit=100):
        response = requests.get(f"{self.base_url}/results", params={
            "min_score": min_score,
            "limit": limit
        })
        return response.json()

# Usage
client = ProductVideoMatchingClient()
job = client.start_job("ergonomic pillows")
print(f"Started job: {job['job_id']}")

# Wait for completion...
status = client.get_job_status(job['job_id'])
print(f"Job status: {status['phase']} ({status['percent']}%)")

# Get results
results = client.get_results(min_score=0.8)
print(f"Found {len(results)} matches")
```

### JavaScript SDK Example

```javascript
class ProductVideoMatchingClient {
  constructor() {
    this.baseUrl = 'http://localhost:8000';
  }

  async startJob(industry, options = {}) {
    const response = await fetch(`${this.baseUrl}/start-job`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        industry,
        topAmz: options.topAmz || 10,
        topEbay: options.topEbay || 5,
        platforms: options.platforms || ['youtube']
      })
    });
    return response.json();
  }

  async getJobStatus(jobId) {
    const response = await fetch(`${this.baseUrl}/status/${jobId}`);
    return response.json();
  }

  async getResults(options = {}) {
    const params = new URLSearchParams({
      min_score: options.minScore || 0.8,
      limit: options.limit || 100
    });
    
    const response = await fetch(`${this.baseUrl}/results?${params}`);
    return response.json();
  }
}

// Usage
const client = new ProductVideoMatchingClient();

async function runExample() {
  const job = await client.startJob('ergonomic pillows');
  console.log(`Started job: ${job.job_id}`);
  
  // Poll for completion
  let status;
  do {
    await new Promise(resolve => setTimeout(resolve, 5000));
    status = await client.getJobStatus(job.job_id);
    console.log(`Job status: ${status.phase} (${status.percent}%)`);
  } while (status.phase !== 'completed' && status.phase !== 'failed');
  
  // Get results
  const results = await client.getResults({ minScore: 0.8 });
  console.log(`Found ${results.length} matches`);
}
```

## OpenAPI Specification

The complete OpenAPI 3.0 specification is available at:
- Main API: `http://localhost:8000/docs`


This provides interactive API documentation and testing capabilities.
