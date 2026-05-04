# Tests

This directory contains the test suite for the backend application.

## Structure

```
tests/
├── conftest.py       # Test configuration and fixtures
├── test_main.py      # Tests for main application
├── test_api/         # API route tests
├── test_services/    # Service layer tests
├── test_models/      # Data model tests
└── README.md         # This file
```

## Test Organization

Tests are organized by application layer:
- **Unit tests**: Individual function testing
- **Integration tests**: Service interaction testing
- **API tests**: Endpoint validation

## Running Tests

To run the test suite:

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_main.py
```

## Test Framework

The test suite uses:
- pytest: Test framework
- pytest-cov: Coverage reporting
- httpx: For API testing
- pytest-asyncio: For async testing

## Writing Tests

Follow these guidelines:
- Use descriptive test function names
- Include docstrings explaining test purpose
- Use fixtures for test data
- Mock external dependencies
- Test both positive and negative cases