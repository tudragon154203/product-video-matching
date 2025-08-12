# Crush Commands & Code Guide

## Build/Test Commands
```bash
# Run all tests
python -m pytest tests/

# Run single test
python -m pytest tests/test_file.py::test_specific_function -v

# Lint (ruff)
ruff check services/ libs/ tests/
ruff format --check services/ libs/ tests/

# Type checking (mypy)
mypy services/*/main.py libs/*/ --ignore-missing-imports
```

## Code Style Guide
- **Imports**: Stdlib → 3rd-party → local, one import per line
- **Types**: Use Python 3.10+ syntax, explicit types on public APIs
- **Naming**: snake_case functions/vars, PascalCase classes, UPPER_SNAKE_CASE constants
- **Error handling**: Use specific exceptions, never bare except:, log with context
- **Formatting**: 88 char line limit, Black-style formatting (configured via ruff)

## Microservice Patterns
All services follow FastAPI + async Postgres + RabbitMQ pattern. Each has:
- main.py with FastAPI app and health endpoints
- requirements.txt with pinned versions
- Dockerfile for containerization
- /health and /metrics endpoints configured