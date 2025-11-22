# Repository Guidelines

## Project Structure & Module Organization
- `services/`: Python microservices. Key services: `main-api` (orchestration), `results-api` (read API), `vision-embedding`, `vision-keypoint`, `video-crawler`, `matcher`, `evidence-builder`, `dropship-product-finder`.
- `libs/`: shared code. Use `libs/common-py/common_py/*` via `PYTHONPATH` in Compose.
- `infra/pvm/`: Docker Compose env (`docker-compose.dev.yml`) and `.env` files.
- `tests/`: integration/system tests (requires infra up). Fixtures in `tests/conftest.py`.
- `scripts/`: utilities like `run_migrations.py`, `seed.py`.
- `data/` and `model_cache/`: local volumes (gitignored) for datasets, models.
- Docs: `README.md`, `RUN.md`, `API.md`, `CONTRACTS.md`.

## Build, Test, and Development Commands
- Bring up dev stack: `docker compose -f infra/pvm/docker-compose.dev.yml up -d --build` (PowerShell: `./up-dev.ps1`).
- Run migrations: `python scripts/run_migrations.py upgrade` (PowerShell: `./migrate.ps1`).
- Seed sample data: `python scripts/seed.py`.
- Tail logs: `docker compose -f infra/pvm/docker-compose.dev.yml logs -f <service>`.
- Stop stack: `docker compose -f infra/pvm/docker-compose.dev.yml down` (PowerShell: `./down-dev.ps1`).

## Coding Style & Naming Conventions
- Python 3.10+. Indentation: 4 spaces; follow PEP 8; prefer type hints.
- Names: snake_case (modules/functions), PascalCase (classes), UPPER_SNAKE_CASE (constants).
- Service layout: each service has `Dockerfile`, `main.py`, `config_loader.py`, `handlers/`, `services/`.
- Tests: `test_*.py`. Keep tests close to features and in root `tests/` for integrations.
- `__init__.py` files should be empty to avoid namespace pollution and import issues.

## Testing Guidelines
- Install test deps: `pip install -r requirements-test.txt`.
- Bring infra up before integration tests.
- Run tests: Always navigate to the microservice directory first:
  ```cmd
  cd services\your-microservice-name
  python -m pytest tests\ -v
  ```
  Use `-k <expr>` to filter tests. Aim for meaningful coverage on core flows.
- Use small fixtures; avoid large media in Git.

## Commit & Pull Request Guidelines
- Commits: concise, imperative summaries; group related changes. Conventional Commits optional (not consistently used in history).
- PRs: include purpose, linked issues (`Closes #123`), test steps, and relevant logs/screenshots.
- Checks: green CI, smoke tests pass (`./smoke.ps1`) before merge; prefer squash-merge.

## Security & Configuration Tips
- Never commit secrets. Copy `infra/pvm/.env.example` → `infra/pvm/.env`; per‑service `.env.example` → `.env`.
- Use Git LFS for large artifacts (videos/models) when versioning.
- Ports: Postgres on `5435`, RabbitMQ UI on `15672`. Adjust in Compose if needed.

## Architecture Overview
- Event‑driven pipeline over RabbitMQ. Postgres + pgvector for storage/search. `main-api` orchestrates jobs; workers emit artifacts consumed by `matcher` and served by `results-api`.

### Job Workflow

#### Starting a New Job
1. **API Request**: POST `/start-job` with request body:
   ```json
   {
     "query": "ergonomic pillows",
     "top_amz": 10,
     "top_ebay": 5,
     "platforms": ["youtube"],
     "recency_days": 365
   }
   ```

2. **Job Initialization** (`main-api` → `JobInitializer`):
   - Generates UUID for `job_id`
   - Uses LLM to classify industry and generate search queries
   - Stores job in database with phase "collection"
   - Publishes two events:
     - `products.collect.request`: For Amazon/eBay product collection
     - `videos.search.request`: For YouTube/Bilibili video search

#### Event-Driven Pipeline
3. **Collection Phase**:
   - `dropship-product-finder` processes `products.collect.request` → scrapes products
   - `video-crawler` processes `videos.search.request` → searches videos, extracts keyframes
   - Services publish completion events:
     - `products.collections.completed`
     - `videos.collections.completed`

4. **Feature Extraction Phase**:
   - `product-segmentor` masks product backgrounds → `products.images.masked.batch`
   - `vision-embedding` generates CLIP embeddings:
     - `image.embeddings.completed` (for products)
     - `video.embeddings.completed` (for video keyframes)
   - `vision-keypoint` extracts AKAZE/SIFT features:
     - `image.keypoints.completed`
     - `video.keypoints.completed`

5. **Matching Phase**:
   - `matcher` receives `match.request` after feature extraction completes
   - Performs product-video matching using vector similarity + geometric verification
   - Publishes `match.result` events for each match
   - Completes with `match.request.completed`

6. **Evidence Phase**:
   - `evidence-builder` creates visual proof of matches
   - Completes with `evidences.generation.completed`

7. **Job Completion**:
   - Main API updates job phase to "completed"
   - Final status available via GET `/status/{job_id}`

### Event Schemas

All events follow JSON schemas in `libs/contracts/contracts/schemas/` with validation via `EventValidator`.

#### Key Request Events
- `products_collect_request`: Initiates product collection
  ```json
  {
    "job_id": "uuid",
    "top_amz": 10,
    "top_ebay": 5,
    "queries": {"en": ["ergonomic pillows", "cushion support"]}
  }
  ```

- `videos_search_request`: Initiates video search
  ```json
  {
    "job_id": "uuid",
    "industry": "furniture",
    "queries": {"vi": ["gối"], "zh": ["枕头"]},
    "platforms": ["youtube", "bilibili"],
    "recency_days": 365
  }
  ```
  Note: The `queries` field must contain at least one language. Both `vi` (Vietnamese) and `zh` (Chinese) are optional, but at least one must be present. Platform-language mapping: YouTube/TikTok use `vi`, Bilibili/Douyin use `zh`.

- `match_request`: Triggers matching process
  ```json
  {
    "job_id": "uuid",
    "event_id": "uuid"
  }
  ```

#### Key Completion Events
- `products_collections_completed`: Product collection finished
- `videos_collections_completed`: Video collection finished
- `image_embeddings_completed`: Product embeddings ready
- `video_embeddings_completed`: Video embeddings ready
- `match_request_completed`: Matching finished
- `evidences_generation_completed`: Evidence generation finished
- `job_completed`: Final job completion
- `job_failed`: Job failure notification

`match_request_completed` is emitted once per job even when zero matches are accepted so the evidence builder can advance and emit `evidences_generation_completed`.

#### Batch Processing Events
- `products_images_masked_batch`: Background removal for multiple product images
- `products_images_ready_batch`: Product images processed
- `video_keyframes_ready_batch`: Video keyframes extracted
- `video_keyframes_masked_batch`: Background removal for keyframes

#### Individual Asset Events
- `image_embedding_ready`, `image_keypoint_ready`: Individual product assets
- `video_embedding_ready`, `video_keypoint_ready`: Individual video assets
- `match_result`: Individual product-video match

All events include:
- `job_id`: Links to the main job
- `event_id`: UUIDv4 for idempotency (required for most events)
- Additional fields specific to each event type

### Microservice Relationships

#### Core Orchestration
- `main-api`: Entry point, job state machine, REST API
  - Receives HTTP requests → converts to events
  - Tracks job phases via database updates
  - Provides status endpoints for monitoring

#### Collection Services
- `dropship-product-finder`: Product scraping
  - Consumes: `products.collect.request`
  - Publishes: `products.collections.completed`
  - Stores: Products, product images in database

- `video-crawler`: Video search and keyframe extraction
  - Consumes: `videos.search.request`
  - Publishes: `videos.collections.completed`, `videos.keyframes.ready`
  - Stores: Videos, video frames in database

#### Processing Services
- `product-segmentor`: Background removal for products
  - Consumes: `products.collections.completed`
  - Publishes: `products.images.masked.batch`
  - Processes: Product images → masked versions

- `vision-embedding`: CLIP-based embedding generation
  - Consumes: `products.images.masked.batch`, `video.keyframes.ready`
  - Publishes: `image.embeddings.completed`, `video.embeddings.completed`
  - Stores: Embeddings in pgvector

- `vision-keypoint`: Traditional CV feature extraction
  - Consumes: `products.images.masked.batch`, `video.keyframes.ready`
  - Publishes: `image.keypoints.completed`, `video.keypoints.completed`
  - Stores: Keypoints and descriptors

#### Matching & Evidence
- `matcher`: Core matching engine
  - Consumes: `match.request` (triggered after feature extraction)
  - Publishes: `match.result`, `match.request.completed`
  - Logic: Vector similarity search + RANSAC geometric verification
  - Stores: Match results in database

- `evidence-builder`: Visual proof generation
  - Consumes: `match.request.completed`
  - Publishes: `evidences.generation.completed`
  - Creates: Composite images showing matched products in video frames

#### Data Flow Summary
```
HTTP Request → main-api → (products + videos) → Collection Services
    ↓
Feature Extraction (segmentation → embeddings + keypoints)
    ↓
Matcher (vector search + geometric verification)
    ↓
Evidence Builder (visual proof)
    ↓
Job Completion → Results available via API
```

### State Management
- Jobs progress through phases: `collection` → `feature_extraction` → `matching` → `evidence` → `completed`/`failed`
- Phase transitions tracked via database and phase events
- Idempotency ensured via `event_id` UUIDs
- Progress percentages: collection (20%), feature_extraction (50%), matching (80%), evidence (90%), completed (100%)

