.PHONY: up-dev down logs seed smoke clean build test help

# Default target
help:
	@echo "Available commands:"
	@echo "  up-dev    - Start all services in development mode"
	@echo "  down      - Stop all services and remove volumes"
	@echo "  logs      - Show logs from all services"
	@echo "  build     - Build all Docker images"
	@echo "  seed      - Seed database with sample data"
	@echo "  smoke     - Run end-to-end smoke test"
	@echo "  migrate   - Run database migrations"
	@echo "  clean     - Clean up Docker resources"
	@echo "  test      - Run integration tests"

# Start development environment
up-dev:
	@echo "Starting development environment..."
	docker compose -f infra/compose/docker-compose.dev.yml up -d --build
	@echo "Waiting for services to be ready..."
	sleep 10
	@echo "Running database migrations..."
	$(MAKE) migrate
	@echo "Services started successfully!"
	docker compose -f infra/compose/docker-compose.dev.yml ps

# Stop development environment
down:
	@echo "Stopping development environment..."
	docker compose -f infra/compose/docker-compose.dev.yml down -v
	@echo "Environment stopped and volumes removed."

# Show logs
logs:
	docker compose -f infra/compose/docker-compose.dev.yml logs -f --tail=200

# Build all images
build:
	@echo "Building all Docker images..."
	docker compose -f infra/compose/docker-compose.dev.yml build

# Run database migrations
migrate:
	@echo "Running database migrations..."
	docker compose -f infra/compose/docker-compose.dev.yml exec -T postgres psql -U postgres -d postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"
	@echo "Migrations completed."

# Seed database with sample data
seed:
	@echo "Seeding database with sample data..."
	python scripts/seed.py
	@echo "Database seeded successfully."

# Run smoke test
smoke:
	@echo "Running end-to-end smoke test..."
	python scripts/smoke_e2e.py
	@echo "Smoke test completed."

# Clean up Docker resources
clean:
	@echo "Cleaning up Docker resources..."
	docker compose -f infra/compose/docker-compose.dev.yml down -v --rmi all
	docker system prune -f
	@echo "Cleanup completed."

# Run integration tests
test:
	@echo "Running integration tests..."
	python -m pytest scripts/tests/ -v
	@echo "Tests completed."

# Quick restart of a specific service
restart-%:
	@echo "Restarting service: $*"
	docker compose -f infra/compose/docker-compose.dev.yml restart $*

# View logs for a specific service
logs-%:
	docker compose -f infra/compose/docker-compose.dev.yml logs -f $*

# Check service health
health:
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health | jq . || echo "Orchestrator: DOWN"
	@curl -s http://localhost:8080/health | jq . || echo "Results API: DOWN"
	@curl -s http://localhost:8081/health | jq . || echo "Vector Index: DOWN"