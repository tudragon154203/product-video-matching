## Development Commands

- `make up-dev`: Start development environment
- `make migrate`: Run database migrations
- `make seed`: Seed sample data
- `make smoke`: Run smoke test
- `make test`: Run integration tests
- `make logs`: View service logs
- `make restart-<service>`: Restart specific service
- `make down`: Stop and remove containers

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
1. Run `make test` to verify changes
2. Run formatter if available
3. Update documentation if needed
4. Commit changes with descriptive message