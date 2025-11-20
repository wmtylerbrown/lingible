# Development Guide

This document covers development practices, testing strategies, and code quality standards for the Lingible backend.

## Development Environment

### Python Environment

**Virtual Environment**:
- Location: `.venv` at project root
- Activation: `source .venv/bin/activate`
- Python Path: `PYTHONPATH=backend/lambda/src` for local development

**Setup**:
```bash
cd /Users/tyler/mobile-app-aws-backend
python -m venv .venv
source .venv/bin/activate
pip install -r backend/lambda/requirements.txt
```

### Dependencies

**Backend**:
- Managed via Poetry (`backend/lambda/pyproject.toml`)
- Install: `cd backend/lambda && poetry install`
- Add dependency: `poetry add <package> && poetry lock && poetry install`

**Infrastructure**:
- Node.js dependencies in `backend/cdk/package.json`
- Install: `cd backend/cdk && npm install`

## Database Initialization

**Initial Setup**: After deploying infrastructure, initialize the database with required data:

1. **Lexicon Terms**: Import from `default_lexicon.json`
2. **Quiz Pools**: Seed wrong answer pools for quiz categories

See [Database Initialization](database-initialization.md) for complete instructions and scripts.

**Quick Start**:
```bash
cd backend/lambda
source ../../.venv/bin/activate
export ENVIRONMENT=dev
export LOG_LEVEL=INFO
export ENABLE_TRACING=false
export LEXICON_TABLE=lingible-lexicon-dev
export PYTHONPATH=src

python src/scripts/init_lexicon.py
python src/scripts/init_quiz_pools.py
```

## Testing

### Test Structure

**Test Directory**: `backend/lambda/tests/`
- All tests use `moto` for AWS service mocking
- Fixtures in `conftest.py` for table schemas and AWS clients
- No test code in `src/` directory

### Running Tests

```bash
source .venv/bin/activate
cd backend/lambda
ENVIRONMENT=test PYTHONPATH=src python -m pytest tests/

# With coverage
ENVIRONMENT=test PYTHONPATH=src python -m pytest tests/ --cov=src --cov-report=html

# Specific test file
ENVIRONMENT=test PYTHONPATH=src python -m pytest tests/test_services.py -v
```

### Test Requirements

**Coverage Targets**:
- Repository services: 90% minimum
- Translation, User, Quiz services: 90% minimum
- Other services: 50% minimum

**Test Types**:
- Use actual Pydantic models (not mocks) for type safety
- Mock AWS services (DynamoDB, Cognito, Secrets Manager) with `moto`
- Build reusable fixtures in `conftest.py`
- Test error handling and edge cases

**TDD Workflow**:
1. Write failing test (Red)
2. Implement minimal code to pass (Green)
3. Refactor for quality (Refactor)

### API Contract Testing

**Purpose**: Ensure database types properly convert to API responses matching OpenAPI spec.

**Implementation**:
- Test model serialization to JSON
- Verify enum values match spec
- Check datetime formatting
- Validate decimal precision

**Example**:
```python
def test_user_response_contract(user_service, mock_user_repo):
    user = user_service.get_user("user_123")
    response = user.to_api_response()
    json_data = response.model_dump_json()

    # Verify JSON matches OpenAPI spec
    assert '"tier":"free"' in json_data
    assert '"status":"active"' in json_data
```

## Code Quality

### Type Safety

**Requirements**:
- All functions must have type hints (parameters and return values)
- Use Pydantic models (not dicts or plain types)
- Strong typing everywhere
- Repository methods return typed objects

**Example**:
```python
def get_user(user_id: str) -> UserProfile:
    return user_service.get_user_profile(user_id)
```

### Enum Usage

**Critical**: Use `str()` to convert enums, not `.value`

```python
# ❌ WRONG
logger.info("Event", extra={"status": status.value})
return {"tier": user_tier.value}

# ✅ CORRECT
logger.info("Event", extra={"status": str(status)})
return {"tier": str(user_tier)}
```

### Import Organization

**Order**:
1. Standard library
2. Third-party
3. Local imports

**Location**: All imports at top of file, never in middle of code

```python
# Standard library
import json
import logging
from typing import Dict, List, Optional

# Third-party
import boto3
from pydantic import BaseModel

# Local imports
from models.user import User
from services.user_service import UserService
```

### Code Formatting

**Black**:
```bash
cd backend/lambda
black src/ tests/
```

**Flake8**:
```bash
flake8 src/ tests/
# Non-test code: ignore only E501 (line too long)
# Test code: ignore F401, F841, E402, E501
```

**MyPy**:
```bash
mypy src/
```

## Logging

### Configuration

**Setup**: Configure logging at Lambda initialization time, not in handlers

**Structured Logging**: Use AWS Lambda Powertools Logger

```python
from aws_lambda_powertools import Logger

logger = Logger(service="my-service")
logger.info("Translation completed", extra={
    "user_id": user_id,
    "character_count": len(text)
})
```

### Logging Strategy

**Log**:
- Errors and exceptions
- Critical business events (account deletion, large operations)
- Security events (auth failures, permission denied)
- Performance issues (slow operations >5 seconds)

**Don't Log**:
- Routine successful operations (every translation, every login)
- Expected behavior (free user translation without storage)
- High-volume events (every database read)

**Goal**: Essential logging only to reduce log volume and costs.

## API Changes

### Mandatory Workflow

**Order** (never skip steps):
1. Update OpenAPI spec: `shared/api/openapi/lingible-api.yaml`
2. Update TypeScript types: `shared/api/types/typescript/api.ts`
3. Regenerate client SDKs:
   - Python: `cd client-sdk && ./regenerate-sdk.sh`
   - Swift: `cd ios && ./regenerate-client-sdk.sh`
4. Update backend code (handlers, services, models)
5. Write/update tests
6. Run all tests

**OpenAPI is the single source of truth** for API contracts.

## Deployment

### CDK Deployment

**Environment-Specific Scripts**:
```bash
cd backend/cdk
npm run synth:dev    # Synthesize dev stack
npm run deploy:dev    # Deploy dev stack
npm run diff:prod     # Diff prod stack
```

**Build Process**:
- `presynth`, `prediff`, `predeploy` automatically run:
  - `npm run build` (TypeScript compilation)
  - `npm run build:lambdas` (Lambda layer/package building)
  - `npm run build:website` (Static website build)

**Docker Required**: Lambda bundling requires Docker Desktop running

### Manual DNS

**After Deployment**:
- Copy DNS instructions from CDK outputs
- Add CNAME records in Squarespace
- Add ACM validation records manually when requested

## Common Patterns

### Repository Pattern

**Purpose**: Abstract data access, provide type-safe interfaces

**Structure**:
```python
class UserRepository:
    def get_user(self, user_id: str) -> User:
        # DynamoDB query logic
        pass

    def create_user(self, user: User) -> User:
        # DynamoDB put logic
        pass
```

### Service Pattern

**Purpose**: Business logic orchestration

**Structure**:
```python
class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def get_user(self, user_id: str) -> UserResponse:
        user = self.user_repo.get_user(user_id)
        return user.to_api_response()
```

### Handler Pattern

**Purpose**: API Gateway integration, request/response handling

**Structure**:
```python
from utils.handler_authorization import HandlerAuthorization

@HandlerAuthorization.require_user
def handler(event, context):
    user_id = event.requestContext.authorizer.claims['sub']
    # Call service layer
    result = service.do_something(user_id)
    return create_success_response(result)
```

## Troubleshooting

### Import Errors

**Problem**: `ModuleNotFoundError`
**Solution**: Set `PYTHONPATH=backend/lambda/src`

### Type Errors

**Problem**: `AttributeError` with enums
**Solution**: Use `str(enum)` not `enum.value`

### Test Failures

**Problem**: Tests fail with `KeyError` or missing attributes
**Solution**: Check fixtures in `conftest.py`, ensure environment variables set

### CDK Build Failures

**Problem**: Docker errors during synth
**Solution**: Start Docker Desktop before running CDK commands

## Best Practices

1. **Write tests first** (TDD: Red-Green-Refactor)
2. **Type everything** (functions, parameters, returns)
3. **Use Pydantic models** (not dicts)
4. **Follow existing patterns** (repository, service, handler)
5. **Update OpenAPI first** (before code changes)
6. **Log sparingly** (errors and critical events only)
7. **Keep functions focused** (single responsibility)
8. **Document complex logic** (inline comments for non-obvious code)
