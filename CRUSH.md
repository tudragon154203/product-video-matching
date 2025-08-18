# CRUSH.md - Repository Guidelines for Product-Video-Matching

## Build, Test & Lint Commands
- **Run all tests**: `python -m pytest tests/ -v`
- **Run a single test**: `python -m pytest tests/test_file.py::test_name -v`
- **Run with short traceback**: `pytest -v --tb=short`
- **Run tests with coverage**: `pytest --cov=path/to/package tests/`
- **Async tests**: Uses pytest-asyncio (auto-configured in pytest.ini)

## Code Style Guidelines
- **Python version**: 3.10+
- **Formatting**: PEP 8 compliant (4-space indentation, 79/99 char lines)
- **Type hints**: Strongly encouraged for all functions/methods
- **Imports**:
  - Group stdlib, third-party, local imports
  - Absolute imports preferred over relative
- **Naming**:
  - snake_case for variables/functions
  - PascalCase for classes
  - UPPER_SNAKE_CASE for constants
- **Error handling**:
  - Use specific exceptions
  - Include context in error messages
  - Use custom exceptions where appropriate
- **Logging**:
  - Structured logging via structlog
  - Meaningful log levels (debug, info, warning, error)
- **Documentation**:
  - Comprehensive docstrings for public APIs
  - Type hints as primary documentation
  - Keep comments up-to-date

## Development Tips
- Pre-commit hooks (if any) run automatically
- Tests must pass before merging
- Keep commits small and focused