# API Documentation

This document provides detailed API documentation for the Product-Video Matching System.
## Updated Service Names

The following services have been renamed as part of our latest update:
- **Catalog Collector** → **Dropship Product Finder**
- **Media Ingestion** → **Video Crawler**

All API endpoints and functionality remain unchanged.

## Base URLs

- **Main API**: `http://localhost:8000`
- **Results API**: `http://localhost:8080`

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
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Results API

### List Results

Get matching results with optional filtering.

**Endpoint:** `GET /results`

**Query Parameters:**
- `industry` (string, optional): Filter by industry keyword
- `min_score` (float, optional): Minimum match score (0.0-1.0)
- `job_id` (string, optional): Filter by specific job
- `limit` (integer, optional, default: 100): Maximum results to return
- `offset` (integer, optional, default: 0): Pagination offset

**Response:**
```json
[
  {
    "match_id": "match-123",
    "job_id": "job-456",
    "product_id": "prod-789",
    "video_id": "vid-101",
    "best_img_id": "img-202",
    "best_frame_id": "frame-303",
    "ts": 45.5,
    "score": 0.87,
    "evidence_path": "/app/data/evidence/match-123.jpg",
    "created_at": "2024-01-15T10:30:00Z",
    "product_title": "Ergonomic Memory Foam Pillow",
    "video_title": "Best Pillows for Neck Pain Review",
    "video_platform": "youtube"
  }
]
```

**Status Codes:**
- `200`: Results retrieved successfully
- `400`: Invalid query parameters
- `500`: Internal server error

### Get Product Details

Get detailed information about a specific product.

**Endpoint:** `GET /products/{product_id}`

**Response:**
```json
{
  "product_id": "prod-789",
  "src": "amazon",
  "asin_or_itemid": "B08XYZ123",
  "title": "Ergonomic Memory Foam Pillow",
  "brand": "ComfortPlus",
  "url": "https://amazon.com/ergonomic-pillow",
  "created_at": "2024-01-15T10:00:00Z",
  "image_count": 3
}
```

**Status Codes:**
- `200`: Product found
- `404`: Product not found
- `500`: Internal server error

### Get Video Details

Get detailed information about a specific video.

**Endpoint:** `GET /videos/{video_id}`

**Response:**
```json
{
  "video_id": "vid-101",
  "platform": "youtube",
  "url": "https://youtube.com/watch?v=abc123",
  "title": "Best Pillows for Neck Pain Review",
  "duration_s": 180,
  "published_at": "2024-01-10T15:30:00Z",
  "created_at": "2024-01-15T10:15:00Z",
  "frame_count": 6
}
```

**Status Codes:**
- `200`: Video found
- `404`: Video not found
- `500`: Internal server error

### Get Match Details

Get detailed information about a specific match.

**Endpoint:** `GET /matches/{match_id}`

**Response:**
```json
{
  "match_id": "match-123",
  "job_id": "job-456",
  "product": {
    "product_id": "prod-789",
    "src": "amazon",
    "asin_or_itemid": "B08XYZ123",
    "title": "Ergonomic Memory Foam Pillow",
    "brand": "ComfortPlus",
    "url": "https://amazon.com/ergonomic-pillow",
    "created_at": "2024-01-15T10:00:00Z",
    "image_count": 3
  },
  "video": {
    "video_id": "vid-101",
    "platform": "youtube",
    "url": "https://youtube.com/watch?v=abc123",
    "title": "Best Pillows for Neck Pain Review",
    "duration_s": 180,
    "published_at": "2024-01-10T15:30:00Z",
    "created_at": "2024-01-15T10:15:00Z",
    "frame_count": 6
  },
  "best_img_id": "img-202",
  "best_frame_id": "frame-303",
  "ts": 45.5,
  "score": 0.87,
  "evidence_path": "/app/data/evidence/match-123.jpg",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Status Codes:**
- `200`: Match found
- `404`: Match not found
- `500`: Internal server error

### Get Evidence Image

Retrieve the evidence image for a match.

**Endpoint:** `GET /evidence/{match_id}`

**Response:** Binary image data (JPEG format)

**Headers:**
- `Content-Type: image/jpeg`
- `Content-Disposition: attachment; filename="evidence_{match_id}.jpg"`

**Status Codes:**
- `200`: Evidence image found
- `404`: Evidence image not found
- `500`: Internal server error

### Get System Statistics

Get overall system statistics.

**Endpoint:** `GET /stats`

**Response:**
```json
{
  "products": 1250,
  "product_images": 3750,
  "videos": 450,
  "video_frames": 2700,
  "matches": 89,
  "jobs": 25
}
```

**Status Codes:**
- `200`: Statistics retrieved successfully
- `500`: Internal server error

### Health Check

Check Results API service health.

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "service": "results-api",
  "timestamp": "2024-01-15T10:30:00Z"
}
```


## Configuration Parameters

### Port Configuration
- Main API: `http://localhost:8000`
- Results API: `http://localhost:8080`
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
- `RETRIEVAL_TOPK`: Number of results to return in vector search (default: 20)

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
        self.results_url = "http://localhost:8080"
    
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
        response = requests.get(f"{self.results_url}/results", params={
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
    this.resultsUrl = 'http://localhost:8080';
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
    
    const response = await fetch(`${this.resultsUrl}/results?${params}`);
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
- Results API: `http://localhost:8080/docs`

This provides interactive API documentation and testing capabilities.
