# Lingible Backend Test Suite

This directory contains comprehensive unit tests for the Lingible backend application.

## 🧪 Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Pytest configuration and fixtures
├── test_models.py           # Tests for Pydantic models
├── test_services.py         # Tests for service layer
├── test_repositories.py     # Tests for repository layer
├── test_utils.py            # Tests for utility modules
├── test_handlers.py         # Tests for Lambda handlers
└── README.md               # This file
```

## 🚀 Quick Start

### Run All Tests
```bash
cd backend
python run_tests.py
```

### Run Unit Tests Only
```bash
python run_tests.py --type unit
```

### Run with Coverage
```bash
python run_tests.py --coverage
```

### Run Verbose Tests
```bash
python run_tests.py --verbose
```

### Run Fast Tests (Skip Slow Markers)
```bash
python run_tests.py --fast
```

## 📋 Test Categories

### 1. **Model Tests** (`test_models.py`)
- **Purpose**: Validate Pydantic model definitions and validation
- **Coverage**: User, Translation, Subscription, and Event models
- **Key Tests**:
  - Model creation with valid data
  - Validation of required fields
  - Enum value validation
  - Optional field handling
  - Invalid data rejection

### 2. **Service Tests** (`test_services.py`)
- **Purpose**: Test business logic in service layer
- **Coverage**: TranslationService, UserService, SubscriptionService
- **Key Tests**:
  - Translation functionality
  - User management operations
  - Subscription handling
  - Error scenarios
  - Premium vs free user logic

### 3. **Repository Tests** (`test_repositories.py`)
- **Purpose**: Test data access layer
- **Coverage**: UserRepository, TranslationRepository, SubscriptionRepository
- **Key Tests**:
  - CRUD operations
  - DynamoDB interactions
  - Error handling
  - Data transformation

### 4. **Utility Tests** (`test_utils.py`)
- **Purpose**: Test utility functions and classes
- **Coverage**: Exceptions, Response utils, Envelopes, Config, Logging
- **Key Tests**:
  - Custom exception hierarchy
  - API response formatting
  - Event envelope parsing
  - Configuration management
  - Logging functionality

### 5. **Handler Tests** (`test_handlers.py`)
- **Purpose**: Test Lambda function handlers
- **Coverage**: All API handlers and Cognito triggers
- **Key Tests**:
  - Successful API calls
  - Error handling
  - Authentication/authorization
  - Request/response formatting

## 🔧 Test Configuration

### Pytest Configuration (`pytest.ini`)
- **Test Discovery**: Automatically finds test files
- **Markers**: Unit, integration, slow, AWS service tests
- **Output**: Verbose with colors and short tracebacks
- **Warnings**: Filtered to reduce noise

### Fixtures (`conftest.py`)
- **Mock AWS Services**: DynamoDB, Cognito, Secrets Manager
- **Sample Data**: Users, translations, subscriptions, events
- **Mock Clients**: Bedrock, DynamoDB, Cognito
- **Configuration**: Test environment setup

## 🎯 Test Coverage Goals

| Component | Target Coverage | Current Status |
|-----------|----------------|----------------|
| Models | 100% | ✅ Complete |
| Services | 90%+ | ✅ Complete |
| Repositories | 90%+ | ✅ Complete |
| Utils | 95%+ | ✅ Complete |
| Handlers | 85%+ | ✅ Complete |
| **Overall** | **90%+** | ✅ **Complete** |

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
@patch('module.external_service')
def test_with_mock(mock_external):
    mock_external.return_value = expected_result
    # Test implementation
```

### 3. **Testing Error Scenarios**
```python
def test_error_handling():
    with pytest.raises(BusinessLogicError):
        service.process_invalid_data()
```

### 4. **Parameterized Tests**
```python
@pytest.mark.parametrize("input,expected", [
    ("valid", True),
    ("invalid", False),
])
def test_validation(input, expected):
    assert validate(input) == expected
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

# Run integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run AWS-related tests
pytest -m aws
```

## 📊 Coverage Reports

### Generate Coverage Report
```bash
python run_tests.py --coverage
```

### Coverage Output
- **Terminal**: Summary with missing lines
- **HTML**: Detailed report in `htmlcov/index.html`
- **Threshold**: Fails if coverage < 80%

### Coverage Areas
- **Line Coverage**: Percentage of code lines executed
- **Branch Coverage**: Percentage of code branches executed
- **Function Coverage**: Percentage of functions called

## 🚨 Common Test Issues

### 1. **Import Errors**
- **Cause**: Missing `__init__.py` files or incorrect paths
- **Solution**: Ensure all directories have `__init__.py` files

### 2. **Mock Configuration**
- **Cause**: Incorrect mock setup or missing patches
- **Solution**: Check mock configuration in `conftest.py`

### 3. **AWS Service Mocks**
- **Cause**: Moto not properly configured
- **Solution**: Use `@mock_dynamodb` decorator or context manager

### 4. **Test Isolation**
- **Cause**: Tests affecting each other
- **Solution**: Use fresh fixtures and proper cleanup

## 🔄 Continuous Integration

### Pre-commit Hooks
Tests are automatically run as part of pre-commit hooks:
- Unit tests
- Code formatting (black)
- Linting (flake8)
- Type checking (mypy)

### CI/CD Pipeline
- **Trigger**: On every commit to main branch
- **Actions**: Run full test suite with coverage
- **Failure**: Prevents deployment if tests fail

## 📝 Adding New Tests

### 1. **Create Test File**
```python
# tests/test_new_feature.py
import pytest
from unittest.mock import Mock, patch

class TestNewFeature:
    def test_new_feature_success(self):
        # Test implementation
        pass
```

### 2. **Add Fixtures** (if needed)
```python
# In conftest.py
@pytest.fixture
def new_feature_fixture():
    return {"data": "value"}
```

### 3. **Run Tests**
```bash
python run_tests.py --type unit
```

### 4. **Update Documentation**
- Add test description to this README
- Update coverage goals if needed

## 🎯 Best Practices

### 1. **Test Naming**
- Use descriptive test names
- Follow pattern: `test_<scenario>_<expected_result>`
- Example: `test_translation_with_empty_text_raises_error`

### 2. **Test Organization**
- Group related tests in classes
- Use clear docstrings
- Keep tests focused and atomic

### 3. **Mocking Strategy**
- Mock external dependencies
- Use realistic test data
- Avoid over-mocking

### 4. **Assertions**
- Use specific assertions
- Test both success and failure cases
- Verify side effects when relevant

### 5. **Test Data**
- Use fixtures for common data
- Create realistic test scenarios
- Avoid hardcoded values

## 🔗 Related Documentation

- [Pytest Documentation](https://docs.pytest.org/)
- [Moto (AWS Mocking)](https://github.com/spulec/moto)
- [Pydantic Testing](https://docs.pydantic.dev/latest/usage/testing/)
- [AWS Lambda Testing](https://docs.aws.amazon.com/lambda/latest/dg/testing-functions.html)

## 📞 Support

For test-related questions or issues:
1. Check this documentation
2. Review existing test patterns
3. Consult the main project documentation
4. Create an issue with test details
