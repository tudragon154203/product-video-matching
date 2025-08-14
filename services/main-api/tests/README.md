# Main API Service Tests

This directory contains tests for the Main API service.

## Test Files

- `test_main_api.py`: Unit tests for helper functions and models
- `test_llm_fallback.py`: Unit tests for LLM service with fallback functionality
- `test_ollama_unit.py`: Unit tests for Ollama-related functions
- `test_ollama.py`: Integration tests for Ollama functionality
- `test_gemini_unit.py`: Unit tests for Gemini-related functions
- `test_gemini.py`: Integration tests for Gemini functionality
- `test_endpoints.py`: Tests for API endpoints (requires running service)
- `run_tests.py`: Test runner script

## Running Tests

### Run all tests

```bash
python tests/run_tests.py
```

### Run unit tests with pytest

```bash
python -m pytest tests/test_main_api.py tests/test_llm_fallback.py tests/test_ollama_unit.py tests/test_gemini_unit.py -v
```

### Run Ollama integration test

```bash
python tests/test_ollama.py
```

### Run Gemini integration test

```bash
python tests/test_gemini.py
```

### Run endpoint tests

```bash
python tests/test_endpoints.py
```

Note: The endpoint tests require the main API service to be running on `http://localhost:8888`.