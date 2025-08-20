---
inclusion: fileMatch
fileMatchPattern: '*docker*|*compose*|*infra*'
---

# Docker Development Guidelines

## Development Environment
- **Base Directory**: All Docker commands run from project root
- **Compose File**: Use `infra/pvm/docker-compose.dev.yml`
- **Environment**: Load from `infra/pvm/.env` file
- **Networks**: All services use `product-video-matching` network

## Service Configuration
- **Build Context**: Always use `../../` (project root) as context
- **Volume Mounts**: 
  - `../../libs:/app/libs` (shared libraries)
  - `../../data:/app/data` (data persistence)
  - `../../services/<name>:/app/app` (live code reloading)
- **Environment**: Set `PYTHONPATH=/app/libs:/app/libs/common-py:/app/libs/contracts`

## Port Mapping
- **Main API**: `${PORT_MAIN}:8000` (default: 8888)
- **Results API**: `${PORT_RESULTS}:8080` (default: 8890)
- **PostgreSQL**: `${PORT_POSTGRES_DB}:5432` (default: 5432)
- **RabbitMQ**: `5672:5672` (AMQP), `15672:15672` (Management)
- **PgWeb**: `${PORT_POSTGRES_UI}:8081` (default: 8081)

## Health Checks
All services must implement health checks:
- **Database**: `pg_isready -U postgres`
- **RabbitMQ**: Check running + alarms + connectivity
- **Applications**: `/health` endpoint returning 200

## Development Workflow
1. **Start**: `docker compose -f infra/pvm/docker-compose.dev.yml up -d`
2. **Logs**: `docker compose -f infra/pvm/docker-compose.dev.yml logs -f <service>`
3. **Restart**: `docker compose -f infra/pvm/docker-compose.dev.yml restart <service>`
4. **Stop**: `docker compose -f infra/pvm/docker-compose.dev.yml down`

## GPU Support
- **Vision Services**: Uncomment GPU deployment configuration
- **Requirements**: NVIDIA Docker runtime installed
- **Fallback**: Services must handle GPU unavailability gracefully

## Data Persistence
- **Volumes**: `postgres_data`, `rabbitmq_data` for persistence
- **Local Data**: `./data` directory mounted for file storage
- **Migrations**: Auto-run on PostgreSQL startup

## Build Optimization
- **Context**: Use `.dockerignore` to exclude unnecessary files
- **Caching**: Layer caching for dependencies
- **Multi-stage**: Use for production builds
- **Shared Libs**: Mount as volumes in development for live updates