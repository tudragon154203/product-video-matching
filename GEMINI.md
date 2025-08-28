# Project: Product-Video Matching System

## Project Overview

This is an event-driven microservices system designed for matching e-commerce products with video content. It leverages computer vision and deep learning techniques to find visual matches between products (e.g., from Amazon/eBay) and video content (e.g., from YouTube). The system employs an image-first approach, combining deep learning embeddings (CLIP) with traditional computer vision techniques (AKAZE/SIFT + RANSAC) to achieve high-precision matching.

**Key Technologies & Architecture:**
*   **Language:** Python
*   **Architecture:** Event-driven microservices
*   **Message Broker:** RabbitMQ
*   **Database:** PostgreSQL with pgvector for vector similarity search
*   **Containerization:** Docker and Docker Compose for development environment
*   **Core Functionality:** Image-first matching, GPU acceleration for embedding generation, evidence generation, and REST APIs for results and system management.

The system is composed of several microservices, including:
*   `main-api`: Job orchestration, state management, and REST API for accessing matching results.
*   `dropship-product-finder`: Handles product collection.
*   `video-crawler`: Processes video content.
*   `vision-embedding`: Generates deep learning features (embeddings).
*   `vision-keypoint`: Extracts traditional computer vision features (keypoints).
*   `matcher`: Contains the core matching logic.
*   `evidence-builder`: Generates visual evidence of matches.

Shared libraries (`contracts`, `common-py`, `vision-common`) are used across services.

## Building and Running

### Prerequisites

*   Docker and Docker Compose
*   Python 3.10+ (for local development)

### Quick Start

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd product-video-matching
    ```

2.  **Start Development Environment:**
    ```bash
    docker compose -f infra/pvm/docker-compose.dev.yml up -d --build

    # Windows PowerShell:
    .\up-dev.ps1
    ```

3.  **Run Database Migrations:**
    ```bash
    python scripts/run_migrations.py

    # Windows PowerShell:
    .\migrate.ps1
    ```

4.  **Seed with Sample Data (Optional):**
    ```bash
    python scripts/seed.py

    # Windows PowerShell:
    .\seed.ps1
    ```

5.  **Run Smoke Test (Optional):**
    ```bash
    python tests/manual_smoke_test.py

    # Windows PowerShell:
    .\smoke.ps1
    ```

### Running Tests

```bash
python scripts/run_tests.py
```

### Common Development Commands

*   **Start services:** `docker compose -f infra/pvm/docker-compose.dev.yml up -d --build`
*   **View logs:** `docker compose -f infra/pvm/docker-compose.dev.yml logs -f` (all services) or `docker compose -f infra/pvm/docker-compose.dev.yml logs -f <service-name>` (specific service, e.g., `docker compose -f infra/pvm/docker-compose.dev.yml logs -f main-api`)
*   **Restart specific service:** `docker compose -f infra/pvm/docker-compose.dev.yml restart <service-name>` (e.g., `docker compose -f infra/pvm/docker-compose.dev.yml restart main-api`)
*   **Check service health:** `curl http://localhost:8000/health` (Main API) or `curl http://localhost:8080/health` (Results API)
*   **Run command in microservice:** `cd services/<microservice_name> && <your_command_here>` (e.g., `cd services/front-end && npm test`). Replace `<microservice_name>` with the actual name of the service and `<your_command_here>` with the command you wish to execute.
*   **Clean up:** `docker compose -f infra/pvm/docker-compose.dev.yml down`

## Development Conventions

*   **Code Style:** Python code adheres to PEP 8 guidelines.
*   **Logging:** Structured logging is used.
*   **Type Hinting:** Type hints are encouraged for improved code clarity and maintainability.
*   **Docstrings:** Public APIs should include comprehensive docstrings.
*   **Event Contracts:** Event schemas and message contracts are defined in `libs/contracts/` and documented in `CONTRACTS.md`.
*   **Project Structure:** Services are located in `services/`, shared libraries in `libs/`, infrastructure configurations in `infra/`, local data storage in `data/`, and development scripts in `scripts/`.
*   **Docker Build Optimization:** The project utilizes `.dockerignore` and optimized Dockerfiles to reduce build times and improve caching. Shared libraries are volume-mounted in development for live updates.
