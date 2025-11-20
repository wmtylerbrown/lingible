# AGENTS.md - Lingible

A guide for AI coding agents working on the Lingible mobile app AWS backend.

## Dev Environment Setup

### Python Environment
- **Virtual Environment**: Always use `.venv` at project root, never nested venvs
- **Activation**: `source .venv/bin/activate` from project root
- **Python Path**: Always set `PYTHONPATH=backend/lambda/src` for local development
- **Environment Variable**: Set `ENVIRONMENT=test` for local testing

```bash
# Complete setup from scratch
cd /Users/tyler/mobile-app-aws-backend
python -m venv .venv
source .venv/bin/activate
pip install -r backend/lambda/requirements.txt
```

### Common Path Issues
- Import errors? Set `PYTHONPATH=backend/lambda/src`
- Module not found? Ensure venv is activated
- Use absolute imports, not relative: `from models.user import User` (not `from ..models.user`)

### Dependencies
- **Backend**: Use Poetry from `backend/lambda/` directory with activated venv
- **Add dependency**: `cd backend/lambda && poetry add <package> && poetry lock && poetry install`
- **Infrastructure**: Use npm from `backend/cdk/` directory

## Testing Instructions

### Running Tests
```bash
# Always run from backend/lambda directory
# NOTE: tests/ directory is deprecated, use tests_v2/ for all new tests
cd backend/lambda
ENVIRONMENT=test PYTHONPATH=src .venv/bin/python -m pytest tests_v2/

# With coverage
ENVIRONMENT=test PYTHONPATH=src .venv/bin/python -m pytest tests_v2/ --cov=src --cov-report=html

# Specific test file
ENVIRONMENT=test PYTHONPATH=src .venv/bin/python -m pytest tests_v2/test_services.py -v
```

### Test Requirements (CRITICAL)
- **TDD Mandatory**: All new code must follow Red-Green-Refactor workflow
- **Coverage**: 90% minimum for repositories, 50%+ for services, 90%+ for translation/user/quiz services
- **Test Types**: Use actual Pydantic models, not mocks
- **Fixtures**: Build reusable fixtures in conftest.py
- **AWS Mocking**: Use moto for DynamoDB, Cognito, Secrets Manager
- **Fake Credentials**: Default fixture sets fake AWS credentials (never use real ones)
- **NO Test Code in src/**: All test code belongs in tests_v2/ directory only
- **Deprecated**: The `tests/` directory is deprecated - all new tests go in `tests_v2/`

## Backend Deployment

### CRITICAL: Always Use npm Scripts
```bash
# NEVER use direct cdk deploy commands
# ALWAYS use package.json scripts

cd backend/cdk
npm run deploy:dev    # Development deployment
npm run deploy:prod   # Production deployment
npm run build         # Build Lambda packages
```

**Why**: Scripts handle proper build processes, environment configuration, and deployment order.

## iOS Development

### Building the App
```bash
# ALWAYS use build script, NEVER use Xcode build button (⌘+B)
cd ios/Lingible
./build_app.sh dev    # Development build
./build_app.sh prod   # Production build
./build_app.sh both   # Both environments
```

**Why**: Script ensures correct environment configuration and `amplify_outputs.json` files.

### Testing on Simulator
- **Target**: Always use iPhone 16 simulator
- **Command**: `xcodebuild -project Lingible.xcodeproj -scheme Lingible -destination 'platform=iOS Simulator,name=iPhone 16' build`

## API Changes (MANDATORY WORKFLOW)

**CRITICAL**: Any backend API changes MUST follow this exact order:

1. **Update OpenAPI Spec**: `shared/api/openapi/lingible-api.yaml`
2. **Update TypeScript Types**: `shared/api/types/typescript/api.ts`
3. **Regenerate Client SDKs**:
   - Python: `cd client-sdk && ./regenerate-sdk.sh`
   - Swift: `cd ios && ./regenerate-client-sdk.sh` (overwrites existing)
4. **Update Backend Code**: Make your Lambda handler changes
5. **Test Everything**: Run all tests

**Never skip steps or change order**. OpenAPI is the single source of truth.

## Python Code Patterns

### Type Safety (CRITICAL)
- **All functions must have type hints**: Parameters and return values
- **Use Pydantic models**: Not dicts or plain types
- **Strong typing everywhere**: Repository methods return typed objects
- **Prefer enums over strings**: Use enums for constants, avoid dict fields

```python
# ✅ CORRECT
def get_user(user_id: str) -> UserProfile:
    return user_service.get_user_profile(user_id)

# ❌ WRONG
def get_user(user_id):
    return user_service.get_user_profile(user_id)  # No type hints
```

### Enum Usage (CRITICAL - Common Mistake)
```python
# ❌ WRONG - This causes AttributeError!
logger.info("Event", extra={"status": status.value})
return {"tier": user_tier.value}

# ✅ CORRECT - Use str() to convert enums
logger.info("Event", extra={"status": str(status)})
return {"tier": str(user_tier)}
```

**Common enums**: `UserTier`, `StoreEnvironment`, `SubscriptionProvider`, `ReceiptValidationStatus`

### Import Organization (CRITICAL)
```python
# ALL imports MUST be at the top of the file
# NEVER put imports in the middle of code or inside functions

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

### DynamoDB Float/Decimal Conversion (CRITICAL)
DynamoDB does not support Python `float` types - it requires `Decimal`. The `LingibleBaseModel` provides automatic conversion:

```python
# ✅ CORRECT - Use to_dynamodb() when writing to DynamoDB
item = model.to_dynamodb()  # Converts float → Decimal
repository.table.put_item(Item=item)

# ✅ CORRECT - serialize_model() for API responses (converts Decimal → float)
api_response = model.serialize_model()  # Converts Decimal → float

# ✅ CORRECT - _normalize_input() automatically converts Decimal → float when reading
user = User(**dynamodb_item)  # Decimal values automatically converted to float

# ❌ WRONG - Don't manually convert in repositories
item["score"] = Decimal(str(score))  # Use model.to_dynamodb() instead

# ❌ WRONG - Don't store float directly
repository.table.put_item(Item={"score": 85.5})  # Will fail - use Decimal
```

**Key Points**:
- Models use `float` for API compatibility
- `to_dynamodb()` converts float → Decimal for storage
- `serialize_model()` converts Decimal → float for API responses
- `_normalize_input()` converts Decimal → float when reading from DB
- Repositories should use `LingibleBaseModel._to_dynamodb_value()` for individual values

### Authorization Pattern
- **Use HandlerAuthorization wrapper**: Never implement validation yourself
- **Services handle user logic**: Pass user_id to services, not handlers
- **Follow translate handler pattern**: It's the reference implementation

### Configuration
- **No hardcoded values**: Read from config service or SSM
- **Tier limits**: Read from `config/tier-limits.json`, never hardcode
- **Secrets/Parameters**: Use AWS Systems Manager Parameter Store (SecureString) for most secrets, Secrets Manager only for Cognito
- **Parameter naming**: Use format `/lingible/{env}/secrets/{name}` (e.g., `/lingible/dev/secrets/apple-iap-private-key`)
- **Cognito IDs**: Pass through config service

## Common Workflows

### Adding a New API Endpoint
1. Update OpenAPI spec first
2. Update TypeScript types
3. Regenerate SDKs
4. Create handler in `backend/lambda/src/handlers/<name>_api/` (API handlers end with `_api`)
5. Write tests in `tests_v2/` directory (TDD: Red-Green-Refactor)
6. Create/update service layer
7. Create/update repository layer
8. Update CDK construct to wire handler
9. Deploy to dev and test

### Handler Naming Conventions
- **API handlers**: End with `_api` (e.g., `quiz_question_api`, `translate_api`)
- **Async handlers**: End with `_async` (e.g., `slang_validation_async`, `export_lexicon_async`)
- **Cognito triggers**: Use descriptive names (e.g., `cognito_post_confirmation_trigger`)

### Adding New Model Fields
1. Define in `backend/lambda/src/models/`
2. Use Pydantic BaseModel with Field validators
3. Add validation logic in model (not handlers)
4. Update any affected services
5. Write tests for validation
6. Update OpenAPI spec if API-facing

### Updating Dependencies
```bash
# Backend
cd backend/lambda
source ../../.venv/bin/activate
poetry add <package>
poetry lock
poetry install

# Infrastructure
cd backend/cdk
npm install <package>
```

## Date & Time Information

### Getting Current Date (CRITICAL)
```bash
# Always use this command to get the current date
date +%Y-%m-%d

# For full timestamp
date +%Y-%m-%d_%H:%M:%S
```

**Why**: Never rely on training data or assumptions about the current date. Always execute the command to get accurate date information.

**When to use**:
- Creating dated files or archives
- Logging current date in commits or documentation
- Any reference to "today" or "current date"
- Timestamping deployments or releases

## Code Quality Checks

### Before Committing
```bash
# Format code
cd backend/lambda
black src/ tests_v2/

# Lint code
flake8 src/ tests_v2/

# Type check
mypy src/

# Run tests
ENVIRONMENT=test PYTHONPATH=src .venv/bin/python -m pytest tests_v2/ --cov=src
```

### Flake8 Configuration
- **Non-test code**: Ignore only E501 (line too long)
- **Test code**: Also ignore F401, F841, E402

## Security Guidelines

### Authentication & Authorization
- **API Gateway Authorizer**: Entry point for all APIs
- **Tier checks**: Always run in authorizer (avoid API invocation costs)
- **Local SAM testing**: Always include Authorization header (even if fake) to trigger authorizer
- **Token validation**: Properly validate JWT tokens

### Secrets Management
- **Parameter Store**: Use AWS Systems Manager Parameter Store (SecureString) for most secrets
- **Secrets Manager**: Only for Cognito User Pool credentials (required by Cognito)
- **Parameter naming**: `/lingible/{env}/secrets/{name}` format
- **Management script**: Use `backend/cdk/scripts/manage-secrets.js` to create/update parameters
- **CDK secrets**: Read from Parameter Store, never embed in code
- **Apple credentials**: Use Parameter Store for App Store keys

## Common Gotchas

### Python
- ❌ Don't use `.value` on Pydantic enums (use `str()`)
- ❌ Don't put imports in middle of files (all imports at top)
- ❌ Don't return dicts (return typed models)
- ❌ Don't create orchestration services for circular deps (fix the deps)
- ❌ Don't hardcode tier limits (use config/tier-limits.json)
- ❌ Don't store float in DynamoDB (use `model.to_dynamodb()` to convert float → Decimal)
- ✅ Use `LingibleBaseModel.to_dynamodb()` for DynamoDB writes (converts float → Decimal)
- ✅ Use `LingibleBaseModel.serialize_model()` for API responses (converts Decimal → float)

### Testing
- ❌ Don't use real AWS credentials in tests
- ❌ Don't put test code in src/ directory
- ❌ Don't use mocks when real models work better

### Deployment
- ❌ Don't use `cdk deploy` directly (use npm scripts)
- ❌ Don't run commands without activating venv
- ❌ Don't use SAM for remote deployments (only local dev)
- ❌ Don't use rapid CLI for image building

### iOS
- ❌ Don't use Xcode build button (use build_app.sh)
- ❌ Don't target iPhone 15 (use iPhone 16)
- ❌ Don't skip environment validation

## File Organization

### Legal/Website Files
- **Legal docs**: Belong in `shared/` directory
- **Website files**: Belong in `website/` directory (public)
- **Build process**: Converts files and publishes to S3/CloudFront via CDK

### Lambda Layers
- **Auto-updated**: Build process handles lambda-layer directory
- **No manual changes**: Don't manually modify lambda-layer/

## Project Structure Quick Reference

```
backend/
├── lambda/
│   ├── src/
│   │   ├── handlers/        # Lambda entry points (API, async, triggers)
│   │   ├── services/        # Business logic
│   │   ├── repositories/    # Data access
│   │   ├── models/          # Pydantic models
│   │   └── utils/           # Shared utilities
│   ├── tests_v2/            # Test suite (tests/ is deprecated)
│   └── tests/               # Deprecated - use tests_v2/
└── cdk/                     # AWS CDK infrastructure

shared/
├── api/
│   └── openapi/            # API specification (source of truth)
├── config/                 # Configuration files
└── legal/                  # Legal documents

ios/
└── Lingible/
    ├── Lingible/           # Swift source code
    └── generated/          # Generated SDK (auto-overwritten)

memory-bank/                # Project knowledge base
├── tasks.md               # Active task tracking
├── progress.md            # Progress updates
├── archive/               # Historical documentation
└── *.md                   # Various context files
```

## Logging

### Configuration
- **Set at initialization**: Configure logging at Lambda init time, not in handlers
- **Structured logging**: Use AWS Lambda Powertools Logger
- **Business events**: Log key operations for analytics
- **No sensitive data**: Never log sensitive information

```python
from aws_lambda_powertools import Logger

logger = Logger(service="my-service")
logger.info("Translation completed", extra={
    "user_id": user_id,
    "character_count": len(text)
})
```

## Memory Bank Usage

### Core Files
- **Active Work**: `memory-bank/tasks.md` (ephemeral, cleared after completion)
- **Progress**: `memory-bank/progress.md`
- **Context**: `memory-bank/activeContext.md`
- **Patterns**: `memory-bank/systemPatterns.md`
- **Tech Details**: `memory-bank/techContext.md`
- **Style Guide**: `memory-bank/style-guide.md`

**All core files are in `memory-bank/` - never create them elsewhere.**

## PR & Commit Guidelines

### Commits
- **NO auto-commits**: Don't commit after every change
- **Include issue references**: Use #issue_number in commit messages
- **Meaningful messages**: Describe what and why, not just what

### Code Review
- **Test coverage required**: PRs rejected without tests
- **Type safety required**: All code must be strongly typed
- **Follow patterns**: Match existing codebase patterns
- **No major changes without discussion**: Ask before big refactors

---

## Quick Reference Commands

```bash
# Test everything
cd backend/lambda && ENVIRONMENT=test PYTHONPATH=src .venv/bin/python -m pytest tests_v2/

# Deploy backend
cd backend/cdk && npm run deploy:dev

# Build iOS
cd ios/Lingible && ./build_app.sh dev

# Regenerate SDKs (after API changes)
cd client-sdk && ./regenerate-sdk.sh
cd ios && ./regenerate-client-sdk.sh

# Add Python dependency
cd backend/lambda && poetry add <package> && poetry lock && poetry install

# Code quality
cd backend/lambda && black src/ tests_v2/ && flake8 src/ tests_v2/ && mypy src/
```

---

**Remember**: When in doubt, check the Memory Bank files in `memory-bank/` for detailed context and patterns.
