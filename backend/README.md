# Lingible Backend

A serverless backend for translating GenZ slang to English and vice versa using AWS Bedrock AI.

## 🏗️ Architecture

- **AWS Lambda** - Python 3.13 serverless functions
- **API Gateway** - REST API endpoints
- **DynamoDB** - Single-table design for data storage
- **AWS Cognito** - User authentication and management
- **AWS Bedrock** - AI translation service
- **AWS CDK** - Infrastructure as Code
- **uv** - Fast, locked Python dependency management (`uv.lock`, hash-verified)

## 📁 Project Structure

```
backend/
├── lambda/                  # Python Lambda functions
│   ├── src/                # Lambda function source code
│   │   ├── handlers/       # Individual Lambda handlers
│   │   ├── models/         # Pydantic models (domain + API)
│   │   ├── services/       # Business logic layer
│   │   ├── repositories/   # Data access layer
│   │   └── utils/          # Utility functions
│   ├── tests/              # Test suite
│   ├── pyproject.toml      # uv dependencies, ruff/mypy config
│   ├── uv.lock             # Locked dependencies (hash-verified)
│   └── cleanup.sh          # Lambda cleanup script
├── cdk/                    # AWS CDK infrastructure
│   ├── src/
│   │   ├── constructs/     # CDK constructs (Shared, Data, Async, Api)
│   │   ├── stacks/         # CloudFormation stacks (Backend, Website)
│   │   └── components/     # Reusable CDK components
│   ├── scripts/            # Build and management scripts
│   └── artifacts/          # Lambda build artifacts
├── scripts/               # Backend utility scripts
│   └── setup-uv.sh        # uv setup script
└── docs/                  # Backend documentation
```

## 🚀 Development Setup

### Prerequisites
- Python 3.13
- Node.js 18+
- AWS CLI configured
- uv (installed via setup script)

### Initial Setup
```bash
# Setup uv and sync the repo-root .venv (first time)
cd backend
./scripts/setup-uv.sh
source ../.venv/bin/activate
```

### Development Workflow
```bash
# From the repo root -- runs ruff format/check + mypy + pytest for backend/lambda
.venv/bin/nox -s lint typecheck test

# Or individually, from backend/lambda
pytest
mypy src/
ruff check src/
ruff format src/

# Add dependencies
uv add boto3                    # Runtime dependency
uv add --group dev pytest       # Dev dependency
```

## 🏗️ Build & Deployment

### Local Development
```bash
cd backend/cdk
npm install
npm run build              # Build TypeScript and Lambda packages
```

### Deploy to AWS
```bash
# Deploy to development
npm run deploy:dev

# Deploy to production
npm run deploy:prod
```

**Stack Structure**: The infrastructure uses a single `BackendStack` that combines all backend resources (Lambda layers, DynamoDB tables, SNS topics, Cognito, API Gateway) to avoid CloudFormation cross-stack reference issues. Logical separation is maintained through internal constructs in `src/constructs/`. The `WebsiteStack` remains separate as it has no dependencies.

### Build Process
1. **uv export**: Generates each layer's `requirements.txt` from `pyproject.toml`/`uv.lock`
2. **uv pip install**: Resolves prebuilt arm64/manylinux wheels for the Lambda runtime directly
   (`--python-platform`/`--only-binary=:all:` -- no Docker daemon needed)
3. **Lambda Layers**: Creates shared dependencies and code layers
4. **Function Packaging**: Bundles individual handlers

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

### System APIs
- `GET /health` - Health check endpoint
- `GET /trending` - Get trending translations

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

### Running Tests
```bash
# All tests
pytest

# Specific test types
pytest tests/unit/
pytest tests/integration/
pytest tests/handlers/

# With coverage
pytest --cov=src --cov-report=html
```

## 🔧 Configuration

### Environment Variables
- **Development**: `dev` environment
- **Production**: `prod` environment
- **Configuration**: Via CDK context and environment variables

### Key Settings
- **Daily Translation Limits**: Free (10), Premium (unlimited)
- **Usage Reset Time**: Midnight Central Time
- **Tier Storage**: Optimized for performance with consistency

## 📚 Documentation

- [`poetry-migration.md`](./docs/poetry-migration.md) - Poetry setup and usage
- [`timezone-change-summary.md`](./docs/timezone-change-summary.md) - Timezone fixes
- [`tier-storage-fix-summary.md`](./docs/tier-storage-fix-summary.md) - Performance optimizations
- [`lambda-optimization.md`](./docs/lambda-optimization.md) - Lambda optimization guide

## 🚨 Important Rules

1. **API Changes**: Always update OpenAPI spec and regenerate client SDKs
2. **Dependencies**: Use uv for all dependency management
3. **Testing**: Maintain 90%+ test coverage
4. **Type Safety**: Use type hints throughout
5. **Performance**: Optimize for frequent operations (get_user_usage)

## 🌐 Environments

- **Development**: `api.dev.lingible.com`
- **Production**: `api.lingible.com`
- **API Gateway**: REST API with custom domain
- **Lambda Runtime**: Python 3.13
