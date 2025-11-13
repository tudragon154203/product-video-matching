# Product-Video Matching System (Sprint 1)

An event-driven microservices system for matching e-commerce products with video content using computer vision and deep learning techniques.

## Overview

This system processes industry keywords to find visual matches between products from Amazon/eBay and video content from YouTube. It uses an image-first approach combining deep learning embeddings (CLIP) with traditional computer vision techniques (AKAZE/SIFT + RANSAC) for high-precision matching.

### Key Features

- **Event-driven architecture** with RabbitMQ message broker
- **Image-first matching** with 95%+ precision at score ≥ 0.80
- **GPU acceleration** for embedding generation (with CPU fallback)
- **Vector similarity search** using PostgreSQL + pgvector
- **Evidence generation** with visual proof of matches
- **Integrated REST API** for job management and results
- **Modern Web UI** built with Next.js and TypeScript
- **Docker Compose** development environment

## Architecture

```
[Client / UI / n8n]
        |
        v
   +-------------------+
   |   Main API        |
   |  (State Machine)  |
   +-------------------+ 
        |
        v
   +-------------------+
   | RabbitMQ (events) |
   | (See CONTRACTS.md)|
   +-------------------+
     /               
    v                 v
+----------------+  +----------------+
| Dropship       |  | Video           |
| Product Finder |  | Crawler         |
| (sản phẩm+ảnh) |  | (video+frames)  |
|  (song song)   |  |  (song song)    |
+----------------+  +----------------+
    |                 |
    v                 v
 (products.image.   (videos.keyframes.
     ready)              ready)
    |                 |
    +--------+--------+
             |
             v
   +-------------------+ 
   | Product Segmentor |
   +-------------------+
             |
             v
 (products.image.   (videos.keyframes.
     masked)             masked)
    |                 |
    +--------+--------+
             |
             v
   +-------------------------------------+
   |   Vision Embedding   || Vision Keypoint   |
   |  (chạy song song)    ||  (chạy song song) |
   +-------------------------------------+
       |
       |
       | (emit image/video       |
       | embeddings)             |
       |                         |
       +-----------+-------------
                   |
                   v
   +-------------------------------+
   |  BARRIER (in Main API)        |
   |  Wait for ALL:               |
   |   - image.embeddings.completed|
   |   - video.embeddings.completed|
      - video.keypoints.completed
      - image.keypoints.completed
   +-------------------------------+
                   |
                   v
   +---------------------------------------------------------+
   |                        Matcher                          |
   |  - Lấy embedding ảnh & video từ PostgreSQL + pgvector   |
   |  - Dùng cosine similarity để tìm top‑K frame gần nhất   |
   |  - Kết hợp với so khớp keypoint (SIFT/ORB + RANSAC) để  |
   |    xác minh hình học                                    |
   |  - Trộn điểm (embedding + keypoint) → final_score       |
   |  - Lọc theo ngưỡng, gộp/đa dạng kết quả                 |
   |  - Phát match.result(.enriched)                         |
   +---------------------------------------------------------+
                   |
                   v
   +-------------------+
   | Evidence Builder  |
   +-------------------+ 
                   |
                   v
              [Client]


## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.10.8 (for development)
- PowerShell (for Windows development scripts)


### 1. Clone and Setup

```bash
git clone <repository-url>
cd product-video-matching
```

### 2. Start Development Environment

```bash
# Windows PowerShell (recommended)
.\_up-dev.ps1

# Or using Docker Compose directly
docker compose -f infra/pvm/docker-compose.dev.yml up -d --build
```

### 3. Run Database Migrations

```bash
# Windows PowerShell
.\_migrate.ps1

# Or run directly
python scripts/run_migrations.py
```

### 4. Run Smoke Test

```bash
# Windows PowerShell
.\_smoke.ps1

# Or run directly (if exists)
python tests/manual_smoke_test.py
```

## Access the Services

Once all services are running:

- **Main API**: http://localhost:8888
- **Web UI**: http://localhost:3000
- **Database UI (pgAdmin)**: http://localhost:8081
- **Redis UI (RedisInsight)**: http://localhost:5540
- **RabbitMQ Management**: http://localhost:15672

## Testing

Each microservice has its own comprehensive test suite with pytest markers for efficient test execution:

### Video Crawler Tests
```bash
cd services/video-crawler
python -m pytest -m unit          # Fast unit tests only
python -m pytest -m integration  # Integration tests with external APIs
python -m pytest -m youtube      # YouTube-specific tests
python -m pytest tests/ -v       # All tests
```

### Dropship Product Finder Tests
```bash
cd services/dropship-product-finder  
python -m pytest -m unit          # Fast unit tests only
python -m pytest -m integration  # Integration with eBay APIs and Redis
python -m pytest tests/ -v       # All tests
```

### Fast Development Workflow
```bash
# Run only unit tests for quick feedback
cd services/video-crawler && python -m pytest -m unit
cd services/dropship-product-finder && python -m pytest -m unit

# Run comprehensive tests before commits
cd services/video-crawler && python -m pytest
cd services/dropship-product-finder && python -m pytest
```

For detailed test documentation, see [CLAUDE.md](CLAUDE.md#testing) and the service-specific README files.

## Usage

### Starting a Matching Job

```bash
curl -X POST http://localhost:8888/start-job \\
  -H "Content-Type: application/json" \\
  -d '{
    "industry": "ergonomic pillows",
    "top_amz": 10,
    "top_ebay": 5,
    "platforms": ["youtube"],
    "recency_days": 365
  }'
```

### Checking Job Status

```bash
curl http://localhost:8888/status/{job_id}
```

### Getting Results

```bash
# All results
curl http://localhost:8888/results

# Filtered results
curl "http://localhost:8888/results?min_score=0.8&industry=pillows"

# Specific match details
curl http://localhost:8888/matches/{match_id}
```

### Viewing Evidence

Evidence images are available at:
```
http://localhost:8888/evidence/{match_id}
```

## API Documentation

### Main API (Port 8888)

- `POST /start-job` - Start a new matching job
- `GET /status/{job_id}` - Get job status and progress
- `GET /results` - List matching results (with filtering)
- `GET /matches/{id}` - Get match details
- `GET /evidence/{match_id}` - Get evidence image
- `GET /products` - Get products with pagination
- `GET /videos` - Get videos with pagination
- `GET /stats` - System statistics
- `GET /health` - Health check

### Web UI (Port 3000)

- Modern React/Next.js interface for job management
- Real-time job progress tracking
- Product and video browsing with pagination
- Interactive match results with evidence images


## Docker Build Optimization

### Build Context Optimization

The Docker build process has been optimized to reduce build times by:

1. **`.dockerignore` file**: Excludes unnecessary directories from the build context
   - Tests, documentation, and temporary files
   - Git history and development tools
   - Large data directories

2. **Optimized Dockerfiles**: Copy only essential files during build
   - Shared libraries are copied first for better caching
   - Requirements are copied before dependencies for layer caching
   - Unnecessary files are excluded from Docker context

### Build Performance

The optimized build process provides significant improvements:
- **Smaller build context**: From ~100MB+ to ~4KB
- **Faster builds**: Reduced file copying and processing
- **Better caching**: Layer reuse for common dependencies

### Building Services

To build a specific service with optimizations:

```bash
# Build with optimized context
docker compose -f infra/pvm/docker-compose.dev.yml build --no-cache <service-name>

# Example: Build main-api
docker compose -f infra/pvm/docker-compose.dev.yml build --no-cache main-api
```

### Build Cache Strategy

The Dockerfiles follow a cache-friendly order:
1. Copy shared libraries (`libs/`)
2. Copy requirements files
3. Install Python dependencies
4. Install shared libraries in development mode
5. Copy application code (if needed)

This allows Docker to cache layers effectively, speeding up subsequent builds when only application code changes.

### Dynamic Library Updates

In development mode, shared libraries in the `libs/` directory are mounted as volumes to enable dynamic updates without rebuilding containers:

- **Volume Mount**: `../../libs:/app/libs` (writable)
- **PYTHONPATH**: Includes `/app/libs`, `/app/libs/common-py`, and `/app/libs/contracts`
- **No Static Installation**: Libraries are not copied into containers during build
- **Live Updates**: Changes to library files are immediately reflected in running services

This allows developers to modify shared library code and see changes take effect immediately without restarting services or rebuilding containers.

## Development

### Project Structure

```
├── services/           # Microservices
│   ├── main-api/      # Job orchestration and integrated API
│   ├── front-end/     # Next.js Web UI (React/TypeScript)
│   ├── dropship-product-finder/  # Product collection
│   ├── video-crawler/    # Video processing
│   ├── vision-embedding/   # Deep learning features
│   ├── vision-keypoint/    # Traditional CV features
│   ├── product-segmentor/  # Image segmentation
│   ├── matcher/           # Core matching logic
│   └── evidence-builder/  # Visual evidence
├── libs/              # Shared libraries
│   ├── contracts/     # Event schemas
│   ├── common-py/     # Common utilities
│   └── vision-common/ # Vision processing
├── infra/             # Infrastructure
│   ├── pvm/           # Docker Compose files
│   ├── migrations/    # Database migrations
│   └── init_db/      # Database initialization
├── data/              # Local data storage
├── scripts/           # Development scripts
├── model_cache/       # Hugging Face model cache
└── docs/              # Documentation and sprint specs
```

### Running Tests

```bash
# Navigate to service directory first, then run:
cd services/video-crawler
python -m pytest -m unit          # Fast unit tests only
python -m pytest -m integration  # Integration tests with external APIs
python -m pytest tests/ -v       # All tests

# Front-end tests
cd services/front-end
npm test                          # Jest unit tests
npm run test:e2e                  # Playwright end-to-end tests
```

### Development Commands

```bash
# Start all services
.\_up-dev.ps1

# Stop all services
.\_down-dev.ps1

# Restart services
.\_restart.ps1

# View logs (use Docker Compose directly)
docker compose -f infra/pvm/docker-compose.dev.yml logs -f main-api
docker compose -f infra/pvm/docker-compose.dev.yml logs -f front-end

# Check service health
curl http://localhost:8888/health

# Code formatting
.\_autopep.ps1                    # Python formatting
.\_flake8.ps1                     # Linting
```

### Adding New Services

1. Create service directory in `services/`
2. Add Dockerfile and requirements.txt
3. Implement service using common libraries
4. Add to docker-compose.dev.yml
5. Update documentation

### Event Contracts

For information about event contracts and message schemas, see [CONTRACTS.md](CONTRACTS.md).

## Configuration

### Environment Variables

Key configuration options (set in `.env`):

```bash
# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5435

# Service Ports
PORT_MAIN=8888          # Main API
PORT_UI=3000            # Web UI
PORT_RESULTS=8080        # (deprecated)
PORT_REDIS=6379         # Redis
PORT_REDIS_UI=5540       # Redis UI
PORT_POSTGRES_UI=8081    # pgAdmin

# Data Paths
DATA_ROOT_HOST=data        # Host path
DATA_ROOT=./data          # Container path
MODEL_CACHE=model_cache   # Hugging Face models

# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### Matching Parameters

The system uses configurable thresholds for matching:

- `RETRIEVAL_TOPK`: Number of candidates from vector search
- `SIM_DEEP_MIN`: Minimum embedding similarity
- `INLIERS_MIN`: Minimum keypoint inliers ratio
- `MATCH_BEST_MIN`: Minimum score for best pair
- `MATCH_CONS_MIN`: Minimum consistency count
- `MATCH_ACCEPT`: Final acceptance threshold

## Monitoring

### Health Checks

All services expose `/health` endpoints:

```bash
curl http://localhost:8888/health  # Main API
```

### Metrics

Basic metrics are available through service endpoints:

```bash
curl http://localhost:8888/stats      # System statistics
```

### Logs

Structured JSON logs are available via Docker Compose:

```bash
# All services
docker compose -f infra/pvm/docker-compose.dev.yml logs -f

# Specific service
docker compose -f infra/pvm/docker-compose.dev.yml logs -f main-api
docker compose -f infra/pvm/docker-compose.dev.yml logs -f front-end
```

## Troubleshooting

### Common Issues

1. **Services not starting**
   - Check Docker daemon is running
   - Verify ports 5435, 5672, 8888, 3000 are available
   - Run `.\_down-dev.ps1` then `.\_up-dev.ps1`

2. **Database connection errors**
   - Ensure PostgreSQL container is healthy
   - Check `.env` file for correct database configuration
   - Run `.\_migrate.ps1` after startup

3. **Web UI not loading**
   - Ensure front-end service is running
   - Check port 3000 availability
   - Verify Main API is accessible on port 8888

4. **No matches found**
   - This is expected with mock data in MVP
   - Check job status for errors
   - Verify all services are healthy

4. **GPU not available**
   - Vision embedding service falls back to CPU
   - Uncomment GPU configuration in docker-compose.dev.yml
   - Ensure NVIDIA Docker runtime is installed

### Debug Mode

Enable debug logging:

Set `LOG_LEVEL=DEBUG` in the `.env` file

### Service Dependencies

Service startup order:
1. PostgreSQL, RabbitMQ, Redis
2. Main API
3. Front-end (depends on Main API)
4. All processing services

## Performance

### Expected Performance (MVP)

- **Throughput**: ~5k keyframes/day on CPU
- **Precision**: ≥95% for matches with score ≥ 0.80
- **Latency**: ~2-5 minutes per job (small datasets)

### Scaling Considerations

- **GPU acceleration**: Significantly improves embedding generation
- **Horizontal scaling**: Services can be replicated
- **Database optimization**: Add indexes for large datasets
- **Caching**: Redis for frequently accessed data

## Security

### Development Security

- Default credentials are for development only
- No authentication in MVP (add for production)
- Local network access only

### Production Considerations

- Use secure credentials and secrets management
- Add authentication and authorization
- Enable TLS/SSL for all communications
- Implement rate limiting and input validation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run integration tests
5. Submit pull request

### Code Style

- Python: Follow PEP 8
- Use structured logging
- Add type hints
- Include docstrings for public APIs

## License

[Add license information]

## Support

For issues and questions:
- Check troubleshooting section
- Review service logs
- Create GitHub issue with details

---

**Note**: This is Sprint 1 MVP with mock implementations for external APIs. Production deployment requires real API integrations and additional security measures.
