# Technical Context

## Technologies
- Python 3.10+ for all services and shared libraries
- Docker/Compose for local orchestration; per-service images
- RabbitMQ as the event broker for contract-driven communication
- Postgres for state, job/phase tracking, and results persistence
- Optional: Redis (used by dropship-product-finder), Qdrant (legacy/optional; vector-index service retired in sprint 9)
- LLM Services: Gemini (primary) with Ollama fallback for production requests

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
  - Results API: `python services/results-api/main.py`
  - Worker services (crawler, keypoint, embedding, matcher, evidence, segmentor): run their `main.py` or service entry script in each folder