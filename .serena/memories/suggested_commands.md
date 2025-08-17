## Development Commands

- `docker compose -f infra/pvm/docker-compose.dev.yml up -d --build`: Start development environment
- `python scripts/run_migrations.py`: Run database migrations
- `python scripts/seed.py`: Seed sample data
- `python tests/manual_smoke_test.py`: Run smoke test
- `python scripts/run_tests.py`: Run integration tests
- `docker compose -f infra/pvm/docker-compose.dev.yml logs -f`: View service logs
- `docker compose -f infra/pvm/docker-compose.dev.yml restart <service>`: Restart specific service
- `docker compose -f infra/pvm/docker-compose.dev.yml down`: Stop and remove containers

## Entrypoints

- Main API: `http://localhost:8888`
- Results API: `http://localhost:8890`

## Utility Commands

- `git`: Version control
- `docker`: Container management
- `docker-compose`: Multi-container orchestration
- `uvicorn`: Run Python services
- `httpx`: HTTP client for testing

## Task Completion

After completing a task:
1. Run `python scripts/run_tests.py` to verify changes
2. Run formatter if available
3. Update documentation if needed
4. Commit changes with descriptive message