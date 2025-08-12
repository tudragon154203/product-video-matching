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
- **REST API** for results and system management
- **Docker Compose** development environment

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   n8n/UI   │───▶│Orchestrator │───▶│ RabbitMQ    │
└─────────────┘    └─────────────┘    │Event Bus    │
                                      └─────┬───────┘
                                            │
        ┌───────────────────────────────────┼───────────────────────────────────┐
        │                                   ▼                                   │
        │   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │
        │   │  Catalog    │    │   Media     │    │   Vision    │              │
        │   │ Collector   │    │ Ingestion   │    │ Embedding   │              │
        │   └─────────────┘    └─────────────┘    └─────────────┘              │
        │                                                                       │
        │   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │
        │   │   Vision    │    │   Vector    │    │   Matcher   │              │
        │   │  Keypoint   │    │   Index     │    │             │              │
        │   └─────────────┘    └─────────────┘    └─────────────┘              │
        │                                                                       │
        │   ┌─────────────┐    ┌─────────────┐                                 │
        │   │  Evidence   │    │ Results API │                                 │
        │   │  Builder    │    │             │                                 │
        │   └─────────────┘    └─────────────┘                                 │
        └───────────────────────────────────────────────────────────────────────┘
                                      │
                              ┌───────▼───────┐
                              │ PostgreSQL +  │
                              │   pgvector    │
                              └───────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.10+ (for development)
- Make (optional, for convenience commands)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd product-video-matching
cp .env.example .env
```

### 2. Start Development Environment

```bash
# Using Make (recommended)
make up-dev

# Or using Docker Compose directly
docker compose -f infra/pvm/docker-compose.dev.yml up -d --build
```

### 3. Run Database Migrations

```bash
make migrate
```

### 4. Seed with Sample Data

```bash
make seed
```

### 5. Run Smoke Test

```bash
make smoke
```

## Usage

### Starting a Matching Job

```bash
curl -X POST http://localhost:8000/start-job \
  -H "Content-Type: application/json" \
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
curl http://localhost:8000/status/{job_id}
```

### Getting Results

```bash
# All results
curl http://localhost:8080/results

# Filtered results
curl "http://localhost:8080/results?min_score=0.8&industry=pillows"

# Specific match details
curl http://localhost:8080/matches/{match_id}
```

### Viewing Evidence

Evidence images are available at:
```
http://localhost:8080/evidence/{match_id}
```

## API Documentation

### Orchestrator API (Port 8000)

- `POST /start-job` - Start a new matching job
- `GET /status/{job_id}` - Get job status and progress
- `GET /health` - Health check

### Results API (Port 8080)

- `GET /results` - List matching results (with filtering)
- `GET /products/{id}` - Get product details
- `GET /videos/{id}` - Get video details
- `GET /matches/{id}` - Get match details
- `GET /evidence/{match_id}` - Get evidence image
- `GET /stats` - System statistics
- `GET /health` - Health check

### Vector Index API (Port 8081)

- `POST /search` - Vector similarity search
- `GET /stats` - Index statistics
- `GET /health` - Health check

## Development

### Project Structure

```
├── services/           # Microservices
│   ├── orchestrator/   # Job orchestration
│   ├── results-api/    # Results REST API
│   ├── catalog-collector/  # Product collection
│   ├── media-ingestion/    # Video processing
│   ├── vision-embedding/   # Deep learning features
│   ├── vision-keypoint/    # Traditional CV features
│   ├── vector-index/       # Similarity search
│   ├── matcher/           # Core matching logic
│   └── evidence-builder/  # Visual evidence
├── libs/              # Shared libraries
│   ├── contracts/     # Event schemas
│   ├── common-py/     # Common utilities
│   └── vision-common/ # Vision processing
├── infra/             # Infrastructure
│   ├── pvm/           # Docker Compose files
│   └── migrations/    # Database migrations
├── data/              # Local data storage
├── scripts/           # Development scripts
└── ops/               # Monitoring configs
```

### Running Tests

```bash
# Integration tests
make test

# Or manually
python scripts/run_tests.py
```

### Development Commands

```bash
# Start services
make up-dev

# View logs
make logs

# Restart specific service
make restart-orchestrator

# View service logs
make logs-orchestrator

# Check service health
make health

# Clean up
make down
```

### Adding New Services

1. Create service directory in `services/`
2. Add Dockerfile and requirements.txt
3. Implement service using common libraries
4. Add to docker-compose.dev.yml
5. Update documentation

## Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Database
POSTGRES_DSN=postgresql://postgres:dev@localhost:5432/postgres

# Message Broker
BUS_BROKER=amqp://guest:guest@localhost:5672/

# Data Storage
DATA_ROOT=./data

# Vision Models
EMBED_MODEL=clip-vit-b32

# Matching Thresholds
RETRIEVAL_TOPK=20
SIM_DEEP_MIN=0.82
INLIERS_MIN=0.35
MATCH_BEST_MIN=0.88
MATCH_CONS_MIN=2
MATCH_ACCEPT=0.80
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
curl http://localhost:8000/health  # Orchestrator
curl http://localhost:8080/health  # Results API
curl http://localhost:8081/health  # Vector Index
```

### Metrics

Basic metrics are available through service endpoints:

```bash
curl http://localhost:8080/stats      # System statistics
curl http://localhost:8081/stats      # Vector index stats
```

### Logs

Structured JSON logs are available via Docker Compose:

```bash
make logs                    # All services
make logs-orchestrator      # Specific service
```

## Troubleshooting

### Common Issues

1. **Services not starting**
   - Check Docker daemon is running
   - Verify ports 5432, 5672, 8000, 8080, 8081 are available
   - Run `make down` then `make up-dev`

2. **Database connection errors**
   - Ensure PostgreSQL container is healthy
   - Check `POSTGRES_DSN` in `.env`
   - Run `make migrate` after startup

3. **No matches found**
   - This is expected with mock data in MVP
   - Check job status for errors
   - Verify all services are healthy

4. **GPU not available**
   - Vision embedding service falls back to CPU
   - Uncomment GPU configuration in docker-compose.dev.yml
   - Ensure NVIDIA Docker runtime is installed

### Debug Mode

Enable debug logging:

```bash
# In .env file
LOG_LEVEL=DEBUG
```

### Service Dependencies

Service startup order:
1. PostgreSQL, RabbitMQ
2. Orchestrator, Results API, Vector Index
3. All processing services

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