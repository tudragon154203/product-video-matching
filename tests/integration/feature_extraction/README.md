# Feature Extraction Integration Tests

This directory contains focused, maintainable integration tests for the feature extraction pipeline, split from the original monolithic test file.

## Test Structure

### 🎭 **Masking Phase Tests** (`test_feature_extraction_masking_phase.py`)
Tests the background removal and masking functionality.
- **Products masking**: Happy path, partial batch handling
- **Video masking**: Keyframe masking pipeline
- **Markers**: `@masking`

### 🧠 **Embedding Extraction Tests** (`test_feature_extraction_embeddings.py`)
Tests CLIP embedding generation from masked images.
- **Image embeddings**: Happy path, single item, corrupted image handling
- **Markers**: `@embeddings`

### 🔑 **Keypoint Extraction Tests** (`test_keypoints_extraction.py`)
Tests traditional computer vision keypoint extraction.
- **Image keypoints**: AKAZE/SIFT feature extraction
- **Video keypoints**: Frame-level keypoint generation
- **Markers**: `@keypoints`

### ⚠️ **Error Handling Tests** (`test_error_handling.py`)
Tests error scenarios, edge cases, and failure recovery.
- **Missing records**: Non-existent database records
- **Corrupted data**: Invalid masked images/files
- **Service failures**: Unavailable services and retries
- **Malformed events**: Invalid event schemas
- **Database constraints**: Constraint violations
- **Markers**: `@error_handling`

### 🔄 **Idempotency Tests** (`test_idempotency.py`)
Tests duplicate handling and event re-processing.
- **Event idempotency**: Masking, embedding, keypoint events
- **Ready event deduplication**: Duplicate ready events
- **Event ID based deduplication**: Same event_id handling
- **Partial retry scenarios**: Mixed success/failure
- **Markers**: `@idempotency`

### 🌊 **End-to-End Tests** (`test_end_to_end_integration.py`)
Tests the complete workflow and pipeline integration.
- **Complete workflow**: All phases from start to finish
- **Phase ordering**: Correct execution sequence
- **Performance baselines**: Timing and metrics
- **Markers**: `@end_to_end`

### 📁 **Original Tests** (`test_original_integration.py`)
The original monolithic test file (preserved for reference).

## Running Tests

### Run All Feature Extraction Tests
```bash
pytest tests/integration/feature_extraction/ -v
```

### Run Specific Test Files
```bash
# Masking tests only
pytest tests/integration/feature_extraction/test_feature_extraction_masking_phase.py -v

# Error handling tests only
pytest tests/integration/feature_extraction/test_error_handling.py -v
```

### Run by Markers
```bash
# Run only masking tests
pytest tests/integration/feature_extraction/ -m masking -v

# Run only embedding tests
pytest tests/integration/feature_extraction/ -m embeddings -v

# Run only keypoint tests
pytest tests/integration/feature_extraction/ -m keypoints -v

# Run only error handling tests
pytest tests/integration/feature_extraction/ -m error_handling -v

# Run only idempotency tests
pytest tests/integration/feature_extraction/ -m idempotency -v

# Run only end-to-end tests
pytest tests/integration/feature_extraction/ -m end_to_end -v
```

### Run by Multiple Markers
```bash
# Run masking and error handling tests
pytest tests/integration/feature_extraction/ -m "masking or error_handling" -v

# Run all phase-specific tests (excluding end-to-end)
pytest tests/integration/feature_extraction/ -m "masking or embeddings or keypoints" -v
```

### Run with Specific Timeouts
```bash
# Quick tests (shorter timeout)
pytest tests/integration/feature_extraction/ -m "not end_to_end" --timeout=180 -v

# Full end-to-end test (longer timeout)
pytest tests/integration/feature_extraction/test_end_to_end_integration.py --timeout=600 -v
```

## Test Markers Summary

| Marker | Purpose | Test Files | Typical Timeout |
|--------|---------|------------|-----------------|
| `@masking` | Background removal tests | `test_feature_extraction_masking_phase.py` | 300s |
| `@embeddings` | CLIP embedding tests | `test_feature_extraction_embeddings.py` | 300s |
| `@keypoints` | Traditional CV tests | `test_keypoints_extraction.py` | 300s |
| `@error_handling` | Error scenarios | `test_error_handling.py` | 300s |
| `@idempotency` | Duplicate handling | `test_idempotency.py` | 300s |
| `@end_to_end` | Complete workflow | `test_end_to_end_integration.py` | 600s |

## Why This Split?

### 🎯 **Better Maintainability**
- Smaller, focused files are easier to understand and modify
- Clear separation of concerns by functionality
- Reduced cognitive load when working with specific features

### ⚡ **Faster Test Execution**
- Run only relevant tests for the feature you're working on
- No need to run the entire pipeline for every change
- Parallel execution of independent test phases

### 🐛 **Easier Debugging**
- Isolate issues to specific phases quickly
- Focused test failures make root cause analysis easier
- Reduced test complexity for individual scenarios

### 📈 **Better Test Coverage**
- Focused test scenarios for each phase
- Comprehensive edge case testing by phase
- Clear test documentation for each component

### 🔄 **Improved CI/CD**
- Phase-specific test runs in CI pipelines
- Faster feedback loops for developers
- Granular test result reporting

## Test Data

All tests rely on synthetic payloads generated by
`tests/integration/support/test_data.py`:

- **Products**: builders for product image records and ready events
- **Videos**: builders for video metadata and keyframe events
- **Completion events**: helper factories for masking, embedding, keypoint completions
- **Error cases**: dynamic utilities to mix valid/invalid data for resilience tests

## Real Services

All tests use **real services** (no mocks) as enforced by the integration test framework:

- **Real PostgreSQL**: Database operations and constraints
- **Real RabbitMQ**: Event publishing and consumption
- **Real microservices**: Actual feature extraction services
- **Real file storage**: Masked images, embedding vectors, keypoint data

## Observability

All tests validate:
- **Logs**: Service logs captured and analyzed
- **Metrics**: Performance and business metrics
- **Error handling**: Graceful failure and recovery
- **Phase transitions**: Correct event ordering and timing

## Contributing

When adding new tests:

1. **Choose the right file**: Add to the appropriate phase-specific test file
2. **Use consistent markers**: Apply the correct pytest markers
3. **Follow naming conventions**: Use descriptive test method names
4. **Validate observability**: Include log and metric validation
5. **Test edge cases**: Consider error scenarios and boundary conditions
6. **Document purpose**: Clear docstrings explaining test intent

For new phases, create new test files following the established patterns.
