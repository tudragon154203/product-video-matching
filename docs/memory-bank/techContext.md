# Technical Context

## Technologies
- Python 3.10+ for all services and shared libraries
- Docker/Compose for local orchestration; per-service images
- RabbitMQ as the event broker for contract-driven communication
- Postgres for state, job/phase tracking, and results persistence (with pgvector for embeddings)
- Optional: Redis (used by dropship-product-finder), Qdrant (legacy/optional; vector-index service retired in sprint 9)
- LLM Services: Gemini (primary) with Ollama fallback for production requests
- Media Processing: yt-dlp for YouTube video downloads, OpenCV for image processing

## Development Setup
- Prereqs: Docker, Docker Compose, Python 3.10+, make (optional)
- Environment:
  - Copy env examples where applicable (e.g., `services/*/.env.example` to `.env`, `services/main-api/.env.example` to `.env`)
  - For infra, use `infra/pvm/docker-compose.dev.yml` to start broker and DB
- Start infra:
  - `docker compose -f infra/pvm/docker-compose.dev.yml up -d`
- Install deps (per service while developing locally), for example:
  - `pip install -r services/main-api/requirements.txt`
  - `pip install -r services/video-crawler/requirements.txt`
  - Repeat for other services you will run locally
- Run migrations:
  - Ensure DB env vars are set for Postgres, then run `python scripts/run_migrations.py`
- Seed/dev data (optional):
  - `python scripts/seed.py` to create basic fixtures if required by tests/dev flows
- Run services locally (examples):
  - Main API: `python services/main-api/main.py`
  - Worker services (crawler, keypoint, embedding, matcher, evidence, segmentor): run their `main.py` or service entry script in each folder

## Shared Libraries
- vision-common: Used by product-segmentor, vision-embedding, and vision-keypoint for job progress tracking, event publishing, and watermark timers
- common-py: Database connections, CRUD operations, messaging, monitoring, and migration utilities
- contracts: JSON Schema definitions for all events and API contracts

## Service-Specific Dependencies
- video-crawler: yt-dlp for YouTube video downloads
- vision services: OpenCV for image processing, various ML models for keypoints/embeddings
- dropship-product-finder: Redis for caching, requests for API calls
- main-api: Gemini/Ollama LLM integration

### Proper Test Execution Workflow

Always navigate to the microservice directory first before running tests:
```cmd
cd services\your-microservice-name
python -m pytest tests\ -v
```

**Why this matters:**
The microservice path is automatically added to PYTHONPATH when executing from its root directory, ensuring:
- Correct module resolution
- Proper configuration loading
- Access to local test fixtures
### Testing Philosophy
- Write only essential tests that verify core functionality
- Focus on integration tests over unit tests where appropriate
- Use mocks to avoid external dependencies
- Test only critical paths and edge cases
- Skip exhaustive testing of all code paths
- Use fixtures for common setup and teardown
- Implement basic smoke tests for API endpoints
- Mock external services like Playwright browser

### Test Structure
- Create minimal test files that mirror the application structure
- Include basic imports and setup in each test file
- Add placeholder test functions with descriptive names
- Test files follow naming convention `test_*.py`
- Keep tests close to features and in root `tests/` for integrations

### Test Coverage Goals
- Ensure basic API contract is tested
- Verify error handling for critical paths
- Test configuration loading
- Skip exhaustive browser automation testing

### Test Execution Requirements
- Always run tests after writing them to verify they pass
- Adjust the codebase and tests if they fail
- A test writing task can only be marked as completed when all tests pass
- Use `python -m pytest` to run tests with appropriate flags