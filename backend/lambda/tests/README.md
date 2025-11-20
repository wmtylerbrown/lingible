# Lingible Backend Test Suite

This directory contains comprehensive unit tests for the Lingible backend application.

## 🧪 Test Structure

```
tests/
├── __init__.py                          # Test package initialization
├── conftest.py                          # Pytest configuration and fixtures
├── test_*.py                            # Module-specific test files
│   ├── test_*_handler.py               # Handler tests (one per handler)
│   ├── test_*_service.py               # Service tests
│   ├── test_*_repository.py            # Repository tests
│   ├── test_*.py                       # Utility and model tests
└── README.md                           # This file
```

## 🚀 Quick Start

### Run All Tests
```bash
source .venv/bin/activate
cd backend/lambda
ENVIRONMENT=test PYTHONPATH=src python -m pytest tests/
```

### Run with Coverage
```bash
ENVIRONMENT=test PYTHONPATH=src python -m pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
```

### Run Specific Test File
```bash
ENVIRONMENT=test PYTHONPATH=src python -m pytest tests/test_translate_api_handler.py -v
```

### Run Verbose Tests
```bash
ENVENVIRONMENT=test PYTHONPATH=src python -m pytest tests/ -v
```

## 📋 Test Categories

### Handler Tests
- **Pattern**: `test_<handler_module>_handler.py`
- **Purpose**: Test Lambda function handlers
- **Examples**:
  - `test_translate_api_handler.py`
  - `test_quiz_history_api_handler.py`
  - `test_export_lexicon_async_handler.py`
- **Key Tests**: Successful API calls, error handling, authentication/authorization

### Service Tests
- **Pattern**: `test_<service>_service.py`
- **Purpose**: Test business logic in service layer
- **Examples**:
  - `test_translation_service.py`
  - `test_user_service.py`
  - `test_quiz_service.py`
- **Key Tests**: Business logic, error scenarios, premium vs free user logic

### Repository Tests
- **Pattern**: `test_<repository>_repository.py`
- **Purpose**: Test data access layer
- **Examples**:
  - `test_user_repository.py`
  - `test_translation_repository.py`
  - `test_lexicon_repository.py`
- **Key Tests**: CRUD operations, DynamoDB interactions, error handling

### Utility Tests
- **Pattern**: `test_<utility_module>.py`
- **Purpose**: Test utility functions and classes
- **Examples**:
  - `test_exceptions.py`
  - `test_response_utils.py`
  - `test_envelopes.py`
  - `test_smart_logger.py`
  - `test_error_codes.py`
- **Key Tests**: Custom exception hierarchy, API response formatting, event envelope parsing

### Config Tests
- **Pattern**: `test_<config>_config.py` or `test_config_service.py`
- **Purpose**: Test configuration models and service
- **Examples**:
  - `test_quiz_config.py`
  - `test_config_service.py`

## 🔧 Test Configuration

### Pytest Configuration (`pytest.ini`)
- **Test Discovery**: Automatically finds test files in `tests/` directory
- **Markers**: Unit, integration, slow, AWS service tests
- **Output**: Verbose with colors and short tracebacks
- **Warnings**: Filtered to reduce noise

### Fixtures (`conftest.py`)
- **Mock AWS Services**: DynamoDB tables created with `moto`
- **Table Fixtures**: `users_table`, `translations_table`, `submissions_table`, `lexicon_table`, `trending_table`
- **Mock Configuration**: `mock_config` fixture for handler tests
- **AWS Credentials**: Fake credentials set automatically to prevent accidental real AWS usage

## 🎯 Test Coverage Goals

| Component | Target Coverage | Notes |
|-----------|----------------|-------|
| Repositories | 90%+ | All repository modules |
| Translation/User/Quiz Services | 90%+ | Priority services |
| Other Services | 50%+ | Other service modules |
| Handlers | 85%+ | All Lambda handlers |
| Utils | 95%+ | Utility modules |

## 🧪 Test Patterns

### 1. **AAA Pattern (Arrange, Act, Assert)**
```python
def test_something():
    # Arrange
    service = MockService()
    input_data = {"key": "value"}

    # Act
    result = service.process(input_data)

    # Assert
    assert result.success is True
    assert result.data["key"] == "value"
```

### 2. **Mocking External Dependencies**
```python
@patch('handlers.translate_api.handler.translation_service')
def test_with_mock(mock_service):
    mock_service.translate_text.return_value = expected_result
    # Test implementation
```

### 3. **Testing Error Scenarios**
```python
def test_error_handling():
    with pytest.raises(BusinessLogicError):
        service.process_invalid_data()
```

## 🔍 Test Markers

### Available Markers
- `@pytest.mark.unit`: Unit tests (fast, isolated)
- `@pytest.mark.integration`: Integration tests (slower, external dependencies)
- `@pytest.mark.slow`: Slow running tests
- `@pytest.mark.aws`: Tests requiring AWS services

### Usage Examples
```bash
# Run only unit tests
pytest -m unit

# Skip slow tests
pytest -m "not slow"
```

## 📊 Coverage Reports

### Generate Coverage Report
```bash
ENVIRONMENT=test ../../.venv/bin/python -m pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
```

### Coverage Output
- **Terminal**: Summary with missing lines
- **HTML**: Detailed report in `htmlcov/index.html`

## 🚨 Common Test Issues

### 1. **Import Errors**
- **Cause**: Missing `__init__.py` files or incorrect paths
- **Solution**: Ensure `PYTHONPATH=src` is set

### 2. **Mock Configuration**
- **Cause**: Incorrect mock setup or missing patches
- **Solution**: Check mock configuration in `conftest.py`, use `mock_config` fixture for handlers

### 3. **AWS Service Mocks**
- **Cause**: Moto not properly configured
- **Solution**: Use table fixtures from `conftest.py` (e.g., `users_table`, `translations_table`)

### 4. **Test Isolation**
- **Cause**: Tests affecting each other
- **Solution**: Use fresh fixtures and proper cleanup

## 📝 Adding New Tests

### 1. **Create Test File**
- **Handler tests**: `test_<handler_module>_handler.py`
- **Service tests**: `test_<service>_service.py`
- **Repository tests**: `test_<repository>_repository.py`
- **Utility tests**: `test_<utility_module>.py`

### 2. **Use Existing Fixtures**
- Import fixtures from `conftest.py`
- Use `mock_config` fixture for handler tests
- Use table fixtures (e.g., `users_table`) for repository tests

### 3. **Follow Test Patterns**
- Use AAA pattern (Arrange, Act, Assert)
- Mock external dependencies
- Test both success and failure cases

## 🎯 Best Practices

1. **Test Naming**: Use descriptive names following `test_<scenario>_<expected_result>` pattern
2. **Test Organization**: Group related tests in classes, use clear docstrings
3. **Mocking Strategy**: Mock external dependencies, use realistic test data, avoid over-mocking
4. **Type Safety**: Use actual Pydantic models, not mocks
5. **Coverage**: Maintain target coverage levels for each component type

## 🔗 Related Documentation

- [Pytest Documentation](https://docs.pytest.org/)
- [Moto (AWS Mocking)](https://github.com/spulec/moto)
- [Pydantic Testing](https://docs.pydantic.dev/latest/usage/testing/)
- [AWS Lambda Testing](https://docs.aws.amazon.com/lambda/latest/dg/testing-functions.html)
