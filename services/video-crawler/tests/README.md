# Tests Overview

This directory contains the test suite for the `video-crawler` microservice. It is organized into `unit`, `integration`, and `contract` tests, along with shared `fixtures` and `data`.

## Structure:
- `unit/`: Contains unit tests for individual components.
- `integration/`: Contains integration tests that verify interactions between components and external services.
- `contract/`: Contains contract tests to ensure adherence to API and event schemas.
- `fixtures/`: Contains shared test fixtures.
- `data/`: Contains static test data.

## Cross-Platform Techniques

The suite is run on both Ubuntu and Windows hosts, so the tests rely on operating-system-neutral primitives to stay stable.

### Temporary Storage and Cleanup
- Uses `tempfile.mkdtemp()` / `tempfile.TemporaryDirectory()` to isolate filesystem state and let Python choose the correct temp root for each OS (see `integration/test_cleanup_integration.py`, `unit/keyframe_extraction/test_keyframe_extractor.py`).
- Cleans up with `shutil.rmtree(..., ignore_errors=True)` to tolerate Windows file-handle quirks while still guaranteeing teardown (`integration/test_cleanup_integration.py`, `unit/tiktok/test_download_logic.py`).
- When a temporary file must survive past its creation context, tests set `delete=False` on `NamedTemporaryFile` so Windows can reopen it safely (`unit/tiktok/test_download_logic.py`).

### Path Handling
- Builds paths with `pathlib.Path` and `.resolve()` so separators, drive letters, and casing follow the host rules (`conftest.py`, `unit/tiktok/test_download_logic.py`, `unit/video_cleanup/test_video_cleanup_manager.py`).
- Converts to strings or uses `os.path.join()` only when a dependency expects native-style paths, letting Python pick the right separator automatically (`integration/test_integration.py`, `unit/platform_queries/test_platform_queries.py`).

### Environment Isolation
- The `tiktok_env_mock` fixture wraps calls with `patch.dict(os.environ, {...})`, ensuring tests never depend on developer-specific environment variables and that path overrides remain portable (`conftest.py`).

### Async Event Loop Management
- `conftest.py` provides a shared `event_loop` fixture that explicitly creates and closes loops via `asyncio.get_event_loop_policy().new_event_loop()`, which avoids Windows/Unix differences in the default policy under pytest.

### Import Path Normalisation
- `conftest.py` amends `sys.path` with the service root and `libs/` directory discovered via `Path.resolve()`, so Python resolves imports the same way inside Docker (Linux) and on local Windows checkouts.

### Running Tests
- From `services/video-crawler/`, run `python -m pytest tests -v` and optionally filter with `-m <marker>` (for example `-m unit`). The command works unchanged on Windows (PowerShell or cmd) and Linux shells.
