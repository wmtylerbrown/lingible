# Lambda Functions - Lingible Backend

This directory contains the Python Lambda functions for the Lingible backend API.

## 📁 Structure

```
lambda/
├── src/                    # Lambda function source code
│   ├── handlers/          # API Gateway Lambda handlers
│   ├── models/            # Pydantic data models
│   ├── repositories/      # Data access layer
│   ├── services/          # Business logic layer
│   └── utils/             # Utility functions
├── tests/                 # Test suite
├── pyproject.toml         # Poetry configuration (dependencies)
├── poetry.lock           # Poetry lock file (generated)
├── pytest.ini           # Pytest configuration
├── mypy.ini             # MyPy type checking configuration
└── cleanup.sh           # Python cleanup script
```

## 🚀 Development

### Setup Environment
```bash
# From project root
cd backend/lambda

# Setup Poetry (first time only)
../scripts/setup-poetry.sh

# Activate Poetry environment
poetry shell

# Run tests
PYTHONPATH=src poetry run pytest

# Run with coverage
PYTHONPATH=src poetry run pytest --cov=src --cov-report=html --cov-report=term-missing

# Clean up Python artifacts (optional)
./cleanup.sh

# Type checking
poetry run mypy src/
```

### Dependency Management
```bash
# Add runtime dependency
poetry add boto3

# Add development dependency
poetry add --group dev pytest

# Remove dependency
poetry remove package-name

# Show installed packages
poetry show

# Export requirements (for Lambda layer)
poetry export --without dev --format=requirements.txt
```

### Test Categories
```bash
# Run all tests
PYTHONPATH=src poetry run pytest

# Run specific test types
PYTHONPATH=src poetry run pytest -m unit
PYTHONPATH=src poetry run pytest -m integration

# Run fast tests only (skip slow markers)
PYTHONPATH=src poetry run pytest -m "not slow"

# Run with verbose output
PYTHONPATH=src poetry run pytest -v

# Run specific test file
PYTHONPATH=src poetry run pytest tests/test_models.py
```

## 🏗️ Architecture

### Clean Architecture Pattern
- **Handlers**: API Gateway Lambda function entry points
- **Services**: Business logic and orchestration
- **Repositories**: Data access and persistence
- **Models**: Pydantic data validation and serialization
- **Utils**: Shared utilities and decorators

### Key Features
- **Type Safety**: Comprehensive type hints throughout
- **Error Handling**: Custom exception hierarchy with decorators
- **Logging**: Structured logging with Lambda Powertools
- **Testing**: 90%+ test coverage with pytest
- **Documentation**: Comprehensive inline documentation

## 📋 API Endpoints

### Translation APIs
- `POST /translate` - Translate text using AWS Bedrock
- `GET /translations` - Get translation history (premium)
- `DELETE /translations/{id}` - Delete specific translation
- `DELETE /translations` - Clear all translations

### User Management
- `GET /user/profile` - Get user profile
- `GET /user/usage` - Get usage statistics
- `POST /user/upgrade` - Upgrade user subscription

### Trending APIs
- `GET /trending` - Get trending terms and analytics

### System APIs
- `GET /health` - Health check endpoint

### Webhook APIs
- `POST /apple-webhook` - Apple App Store webhook for subscription events

### Background Jobs
- `trending_job` - Scheduled job to update trending terms
- `user_data_cleanup` - Scheduled job to clean up user data

## 🔐 Security

- **Authentication**: JWT tokens via AWS Cognito
- **Authorization**: API Gateway authorizer with user context
- **Input Validation**: Pydantic models for all requests/responses
- **Error Handling**: Secure error responses without data leakage

## 🧪 Testing

### Test Coverage Requirements
- **Minimum**: 90% code coverage
- **Critical Logic**: 100% coverage
- **New Features**: Must include tests
- **Bug Fixes**: Must include regression tests

### Test Categories
- **Unit Tests**: Individual component testing
- **Integration Tests**: Component interaction testing
- **Handler Tests**: API endpoint testing
- **Model Tests**: Data validation testing

## 📦 Deployment

Lambda functions are deployed via AWS CDK from the `../infrastructure/` directory.

### Build Process
1. **Source Code**: Python Lambda functions in `src/`
2. **Packaging**: CDK packages functions for deployment
3. **Deployment**: CDK deploys to AWS Lambda

### Environment Configuration
- **Development**: `dev` environment
- **Production**: `prod` environment
- **Configuration**: Via CDK context and environment variables

## 🔧 Development Workflow

### TDD Workflow (Mandatory)
1. **RED**: Write failing tests first
2. **GREEN**: Write minimal code to pass tests
3. **REFACTOR**: Clean up code while keeping tests green

### Code Quality
- **Linting**: flake8 for style and complexity
- **Type Checking**: mypy for type safety
- **Formatting**: Black for consistent formatting
- **Pre-commit**: Automated quality checks (installed via Poetry)

#### Pre-commit Setup
Pre-commit hooks are automatically installed when you run `poetry install`. The hooks include:
- **Black**: Code formatting
- **Flake8**: Linting and style checks
- **MyPy**: Type checking
- **Trailing whitespace**: Remove trailing spaces
- **End-of-file**: Ensure files end with newline
- **YAML validation**: Check YAML syntax
- **Large files**: Prevent large files from being committed
- **Merge conflicts**: Detect merge conflict markers

To manually install pre-commit hooks:
```bash
# From project root
pre-commit install
```

### Workspace Cleanup
```bash
# Clean Python artifacts and cache files
./cleanup.sh
```

This removes:
- Python cache files (`*.pyc`, `__pycache__/`)
- Test cache (`.pytest_cache/`, `.mypy_cache/`)
- Coverage reports (`.coverage`, `htmlcov/`)
- Build artifacts (`build/`, `dist/`, `*.egg-info/`)
- Temporary files (`*.log`, `*.tmp`, `*.swp`, `*.swo`)
- System files (`.DS_Store`, `Thumbs.db`)

## 📚 Related Documentation

- [API Documentation](../docs/)
- [Infrastructure Setup](../infrastructure/README.md)
- [Project Overview](../../README.md)
- [Memory Bank](../../memory-bank/)
