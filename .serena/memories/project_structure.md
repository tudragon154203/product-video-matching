## Project Structure

- `services/`: Microservices
  - `main-api/`: Job orchestration
  - `results-api/`: Results REST API
  - `catalog-collector/`: Product collection
  - `media-ingestion/`: Video processing
  - `vision-embedding/`: Deep learning features
  - `vision-keypoint/`: Traditional CV features
  - `matcher/`: Core matching logic
  - `evidence-builder/`: Visual evidence
- `libs/`: Shared libraries
  - `contracts/`: Event schemas
  - `common-py/`: Common utilities
  - `vision-common/`: Vision processing
- `infra/`: Infrastructure
  - `pvm/`: Docker Compose files
  - `migrations/`: Database migrations
- `scripts/`: Development scripts
- `ops/`: Monitoring configs