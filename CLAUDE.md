# ìCLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This is an event-driven microservices system for matching e-commerce products with video content using computer vision and deep learning techniques. The system uses an image-first approach combining CLIP embeddings with traditional computer vision (AKAZE/SIFT + RANSAC) for high-precision matching.

### Core Architecture

- **Event-driven**: RabbitMQ message broker for service communication
- **State machine**: Main API manages job orchestration and transitions
- **Vector search**: PostgreSQL + pgvector for embedding similarity search
- **Pipeline processing**: Events flow through product collection → video crawling → segmentation → embedding → matching → evidence generation
- **Dual approach**: Deep learning embeddings (CLIP) + traditional CV features (keypoints)

### Service Dependencies

```
Main API (orchestrator)
    ↓
RabbitMQ (message broker)
    ↓
Dropship Product Finder → Product Segmentation → Vision Embedding/Keypoint
    ↓                                   ↓
Video Crawler → Keyframe Extraction → Matcher → Evidence Builder → [Results API Deprecated]
```

## Development Commands

### Quick Start

```bash
# Start entire development environment
./up-dev.ps1               # Windows PowerShell
docker compose -f infra/pvm/docker-compose.dev.yml up -d --build  # Direct Docker

# Run database migrations
./migrate.ps1             # Windows PowerShell
python scripts/run_migrations.py

# Seed with sample data
./seed.ps1                # Windows PowerShell
python scripts/seed.py

# Run smoke test
./smoke.ps1               # Windows PowerShell
python tests/manual_smoke_test.py

# Development environment control
./down-dev.ps1            # Stop all services
./restart.ps1             # Restart services
```

## Job Initiation and Workflow

### Starting a New Job

The system supports two main job types:
1. **Product-Only Jobs**: Query Amazon/eBay for products only
2. **Video-Only Jobs**: Search video platforms for content only
3. **Mixed Jobs**: Both product collection and video search

#### API Endpoint
```bash
curl -X POST http://localhost:8888/start-job \
  -H "Content-Type: application/json" \
  -d '{
    "query": "ergonomic pillows",
    "industry": "furniture",
    "top_amz": 10,
    "top_ebay": 5,
    "platforms": ["youtube"],
    "recency_days": 365
  }'
```

#### Job Status Monitoring
```bash
# Check job status
curl http://localhost:8888/status/{job_id}

# List all jobs
curl http://localhost:8888/jobs

# Get job videos (after completion)
curl http://localhost:8888/jobs/{job_id}/videos

# Get video frames
curl http://localhost:8888/jobs/{job_id}/videos/{video_id}/frames
```

### Job Phases and Progress

Jobs progress through these phases:
1. **Collection** (20%): Product scraping and video search
2. **Feature Extraction** (50%): Background removal, embeddings, keypoint extraction
3. **Matching** (80%): Product-video similarity matching
4. **Evidence** (90%): Visual proof generation
5. **Completed** (100%): Job finished with results

#### Response Format
```json
{
  "job_id": "uuid",
  "phase": "matching",
  "percent": 80.0,
  "counts": {
    "products": 15,
    "videos": 25,
    "images": 45,
    "frames": 1250
  },
  "collection": {
    "products_done": true,
    "videos_done": true
  },
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### Individual Commands

```bash
# Build specific service
docker compose -f infra/pvm/docker-compose.dev.yml build --no-cache <service-name>

# View service logs
docker compose -f infra/pvm/docker-compose.dev.yml logs -f main-api

# Check health endpoints
curl http://localhost:8888/health  # Main API
```

### Testing

#### Proper Test Execution Workflow

**Always navigate to the microservice directory first before running tests:**

```cmd
cd services\your-microservice-name
python -m pytest tests\ -v
```

**Why this matters:**
The microservice path is automatically added to PYTHONPATH when executing from its root directory, ensuring:

- Correct module resolution
- Proper configuration loading
- Access to local test fixtures

#### Test Commands

```bash
# Run integration tests
python scripts/run_tests.py
pytest tests/
python tests/manual_smoke_test.py

# Test specific service
docker compose -f infra/pvm/docker-compose.dev.yml run --rm main-api python -m pytest

# API integration tests
pytest tests/test_api_integration.py

# Run tests from microservice directory (recommended)
cd services\main-api
python -m pytest tests\ -v

## Pytest Test Markers

Each microservice uses pytest markers for organizing and filtering tests by category:

### Marker Categories
- `unit`: Unit tests (fast, isolated) - **Recommended for most development**
- `integration`: Integration tests (slower, may require external dependencies)
- `youtube`: YouTube-specific tests (video crawler only)
- `real_api`: Tests requiring real API access (skipped by default)
- `slow`: Slow tests that take longer to run

### Marker-Based Test Execution

**Video Crawler Service:**
```bash
cd services\video-crawler
# Run only unit tests (fastest, most common)
python -m pytest -m unit

# Run only integration tests
python -m pytest -m integration

# Run only YouTube tests
python -m pytest -m youtube

# Run all tests (unit + integration + YouTube)
python -m pytest tests\ -v
```

**Dropship Product Finder Service:**
```bash
cd services\dropship-product-finder
# Run only unit tests (fastest, most common)
python -m pytest -m unit

# Run only integration tests
python -m pytest -m integration

# Run all tests (unit + integration)
python -m pytest tests\ -v
```

**All Microservices (best practices):**
```bash
# Fast development workflow - run only unit tests
cd services\video-crawler && python -m pytest -m unit
cd services\dropship-product-finder && python -m pytest -m unit

# Before committing - run all tests including integration
cd services\video-crawler && python -m pytest
cd services\dropship-product-finder && python -m pytest
```
```

#### Testing Philosophy

- Write only essential tests that verify core functionality
- Focus on integration tests over unit tests where appropriate
- Use mocks to avoid external dependencies
- Test only critical paths and edge cases
- Skip exhaustive testing of all code paths
- Use fixtures for common setup and teardown
- Implement basic smoke tests for API endpoints
- Mock external services like Playwright browser

#### Test Structure

- Create minimal test files that mirror the application structure
- Include basic imports and setup in each test file
- Add placeholder test functions with descriptive names
- Test files follow naming convention `test_*.py`
- Keep tests close to features and in root `tests/` for integrations

#### Test Coverage Goals

- Ensure basic API contract is tested
- Verify error handling for critical paths
- Test configuration loading
- Skip exhaustive browser automation testing

#### Test Execution Requirements

- Always run tests after writing them to verify they pass
- Adjust the codebase and tests if they fail
- A test writing task can only be marked as completed when all tests pass
- Use `python -m pytest` to run tests with appropriate flags in microservice's directory

## Event-Driven Architecture

### Event Communication

All services communicate via RabbitMQ topic exchange using structured events:

#### Event Schema Location
- All JSON schemas defined in `libs/contracts/contracts/schemas/`
- Validation enforced by `EventValidator` class
- Supports both underscore (`image_embeddings_completed`) and dot notation (`image.embeddings.completed`)

#### Event Routing Key Patterns
- `products.*.*`: Product-related events
- `videos.*.*`: Video-related events
- `image.*.*`: Image processing events
- `video.*.*`: Video processing events
- `match*.*.*`: Matching events
- `job.*`: Job lifecycle events

#### Idempotency
- All events include `event_id` (UUIDv4) for exactly-once processing
- Services track processed events to prevent duplicate operations
- Critical for reliability in distributed system

### Service Interactions

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   main-api      │    │ RabbitMQ Broker │    │  PostgreSQL     │
│   (REST API)   │◄──►│   (Topic Exchange)│◄──►│ + pgvector     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Product Finder  │    │ Video Crawler   │    │ Product         │
│ (Scraping)     │    │ (Keyframes)     │    │ Segmentator     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Vision          │    │ Vision          │    │ Matcher         │
│ Embedding       │    │ Keypoint       │    │ (Similarity +   │
│ (CLIP)         │    │ (AKAZE/SIFT)   │    │  RANSAC)        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐
│ Evidence        │
│ Builder        │
│ (Visual Proof) │
└─────────────────┘
```

## Key Technologies & Libraries

### Shared Libraries

- `libs/common-py/`: Common utilities for logging, monitoring, CRUD operations
- `libs/contracts/`: Event schemas and validation with JSON Schema
- `libs/vision-common/`: Vision processing utilities and shared CV functions

### Vision Processing

- **Embeddings**: CLIP (OpenAI), GPU/CPU support with pgvector storage
- **Segmentation**: RMBG (Remove Background) and YOLO models for product masking
- **Keypoints**: AKAZE, SIFT, ORB feature extraction with descriptor storage
- **Matching**: Cosine similarity search + RANSAC geometric verification
- **Dual Approach**: Deep learning embeddings + traditional CV for robustness

### Infrastructure

- **Database**: PostgreSQL with pgvector extension for vector similarity search
- **Message Broker**: RabbitMQ with topic exchange for event routing
- **Caching**: Redis for job progress tracking and temporary state
- **Model Cache**: Hugging Face models cached in `model_cache/` directory
- **Web UI**: pgAdmin (port 8081), RedisInsight (port 5540), RabbitMQ UI (port 15672)
- **Development Scripting**: PowerShell scripts for common operations

### Data Storage

- **Products Table**: Product metadata, ASIN/item IDs, titles, brands
- **Videos Table**: Video metadata, platform info, duration, keyframe counts
- **Images Table**: Product image paths, masking status, embedding vectors
- **Video Frames Table**: Frame timestamps, local paths, embedding vectors
- **Matches Table**: Product-video match results with scores and evidence
- **Jobs Table**: Job lifecycle tracking with phases and timestamps

## Project Structure

```
├── services/               # Microservices
│   ├── main-api/         # FastAPI job orchestration
│   ├── results-api/      # REST API for results (deprecated)
│   ├── dropship-product-finder/  # Amazon/eBay scraping
│   ├── video-crawler/     # YouTube video processing
│   ├── vision-embedding/  # CLIP embeddings
│   ├── vision-keypoint/   # Traditional CV features
│   ├── product-segmentor/ # Image segmentation
│   ├── matcher/          # Core matching engine
│   └── evidence-builder/ # Visual proof generation
├── libs/                # Shared libraries (mounted as volumes)
│   ├── contracts/      # Event schemas
│   ├── common-py/      # Common utilities
│   └── vision-common/  # Vision utilities
├── infra/              # Infrastructure config
│   ├── pvm/           # Docker Compose
│   └── migrations/    # Alembic migrations
├── data/              # File storage (mounted volume)
├── scripts/           # Development scripts
└── model_cache/      # Hugging Face models
```

## Service Development Patterns

### Service Template

Each service follows this structure:

- `app/main.py`: Entry point
- `handlers/`: Event handlers for RabbitMQ
- `services/`: Business logic layer
- `config_loader.py`: Environment configuration
- `Dockerfile`: Container build
- `.env`: Service environment variables

### Event Contracts

Events are defined in `libs/contracts/contracts/schemas/` with:

- JSON schema validation
- Dotted routing keys (e.g., `image.embeddings.completed`)
- Topic exchange routing
- Required `event_id` for idempotency

### Configuration

- Shared environment in `.env` (ports, database, etc.)
- Service-specific in `services/<service>/.env`
- Python path includes shared libraries
- Volume mounts for live development

### Data Flow

1. **Job Start**: Main API creates job, triggers product/video collection
2. **Segmentation**: Products/videos masked for background removal
3. **Feature Extraction**: Embeddings (CLIP) + keypoints (AKAZE/SIFT)
4. **Matching**: Vector search + geometric verification
5. **Evidence**: Visual proof generation
6. **Results**: REST API for querying matches (deprecated)

## Environment Configuration

### Required Environment Variables

```bash
# Database credentials should be set in production
POSTGRES_USER=postgres
POSTGRES_PASSWORD=_secure_password_here_
POSTGRES_DB=postgres
PORT_POSTGRES=5435

# Message Broker credentials should be set in production
RABBITMQ_DEFAULT_USER=guest
RABBITMQ_DEFAULT_PASS=guest

# Ports
PORT_MAIN=8888
PORT_RESULTS=8080
PORT_POSTGRES_UI=8081
PORT_REDIS=6379
PORT_REDIS_UI=5540

# Paths
DATA_ROOT=./data
MODEL_CACHE=model_cache
```

### Model Cache

Hugging Face models are cached in `model_cache/` to avoid repeated downloads:

- CLIP models for embeddings
- RMBG for background removal
- YOLO for segmentation

## Development Tips

### Python Module Organization

- `__init__.py` files should be empty to avoid namespace pollution and import issues

### Adding New Services

1. Create service directory in `services/`
2. Add Dockerfile and requirements.txt
3. Implement event handlers following existing patterns
4. Add to docker-compose.dev.yml with proper dependencies
5. Update CONTRACTS.md for event schemas

### Building Services

- Services mount shared libraries as volumes for live updates
- Use `--no-cache` for clean builds
- GPU support available for vision services (uncomment in docker-compose)

### Debugging

- Use health endpoints for service status
- Check RabbitMQ management UI (localhost:15672)
- View pgAdmin for database inspection (localhost:8081)
- Enable debug logging via `LOG_LEVEL=DEBUG`
- Use Docker Compose logs: `docker compose -f infra/pvm/docker-compose.dev.yml logs -f <service>`

### Testing API Endpoints

```bash
# Start matching job
curl -X POST http://localhost:8888/start-job \
  -H "Content-Type: application/json" \
  -d '{
    "industry": "ergonomic pillows",
    "top_amz": 10,
    "top_ebay": 5,
    "platforms": ["youtube"],
    "recency_days": 365
  }'

# Get results (deprecated - use main API endpoints instead)
# curl http://localhost:8080/results?min_score=0.8
```

## Important Notes

- This is a production-ready MVP with optimized Docker builds
- Services share common libraries via volume mounts (no static installation)
- GPU acceleration available for vision processing services
- Event schemas enforce validation and forward compatibility
- Development environment uses mock data for testing
- Production deployment requires real API integrations
- Don't rebuild container if not needed. Just restart
- DO NOT use tools that require ability to read images
