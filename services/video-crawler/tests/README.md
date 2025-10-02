# Tests Overview

This directory contains the test suite for the `video-crawler` microservice. It is organized into `unit`, `integration`, and `contract` tests, along with shared `fixtures` and `data`.

## Structure:
- `unit/`: Contains unit tests for individual components.
- `integration/`: Contains integration tests that verify interactions between components and external services.
- `contract/`: Contains contract tests to ensure adherence to API and event schemas.
- `fixtures/`: Contains shared test fixtures.
- `data/`: Contains static test data.

## Cross-Platform Compatibility

The tests in this directory are designed to work on both Ubuntu and Windows platforms. Key compatibility features include:

### File Path Handling
- Uses Python's `pathlib.Path` for cross-platform path handling that automatically handles differences between Unix-style paths (Ubuntu) and Windows-style paths
- Configuration uses `os.path.join()` which adapts to the underlying OS path separators
- For temporary directories, the service uses `tempfile.TemporaryDirectory()` which handles OS-specific temp locations

### Environment Variables
- Relies on `.env` files loaded via `python-dotenv` which works consistently across both platforms
- Configuration values are loaded from environment variables using `os.getenv()`, which functions identically on both systems
- Platform-agnostic path logic that adapts to each platform's filesystem conventions

### Python Path Configuration
- Adds appropriate paths to `sys.path` conditionally based on the system location
- Handles imports from `libs` directory using both container paths and relative paths for local development
- Pytest configuration sets `pythonpath` to ensure consistent module discovery

### Asyncio Configuration
- Uses `asyncio_mode = auto` in pytest configuration which handles event loop setup automatically
- Includes custom `event_loop` fixture that creates and closes event loops properly on both platforms

### Running Tests
- Both systems can run tests using the same command: `python -m pytest -m unit`
- Pytest markers work consistently across platforms
- Test discovery patterns are configured to work identically on both systems
