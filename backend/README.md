# Lingible Backend

A serverless backend for translating GenZ slang to English and vice versa using AWS Bedrock AI.

## 🏗️ Architecture

- **AWS Lambda** - Python 3.13 serverless functions
- **API Gateway** - REST API endpoints  
- **DynamoDB** - Single-table design for data storage
- **AWS Cognito** - User authentication and management
- **AWS Bedrock** - AI translation service
- **AWS CDK** - Infrastructure as Code
- **Poetry** - Modern Python dependency management

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
│   ├── pyproject.toml      # Poetry dependencies
│   ├── poetry.lock         # Locked dependencies
│   └── setup-poetry.sh     # Poetry setup script
├── infrastructure/         # AWS CDK infrastructure
│   ├── constructs/         # CDK constructs
│   ├── scripts/           # Build scripts
│   └── lambda-layer/      # Shared code layer
└── docs/                  # Backend documentation
```

## 🚀 Development Setup

### Prerequisites
- Python 3.13
- Node.js 18+
- AWS CLI configured
- Poetry (installed via setup script)

### Initial Setup
```bash
# Setup Python virtual environment (first time)
python3.13 -m venv .venv
source .venv/bin/activate

# Setup Poetry and dependencies
cd backend/lambda
./setup-poetry.sh          # Install Poetry and dependencies
poetry shell               # Activate Poetry environment
```

### Development Workflow
```bash
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Type checking
poetry run mypy src/

# Linting
poetry run flake8 src/

# Add dependencies
poetry add boto3            # Runtime dependency
poetry add --group dev pytest  # Dev dependency
```

## 🏗️ Build & Deployment

### Local Development
```bash
cd backend/infrastructure
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

### Build Process
1. **Poetry Export**: Generates `requirements.txt` from `pyproject.toml`
2. **CDK Docker Bundling**: Installs dependencies in Lambda-compatible environment
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
poetry run pytest

# Specific test types
poetry run pytest tests/unit/
poetry run pytest tests/integration/
poetry run pytest tests/handlers/

# With coverage
poetry run pytest --cov=src --cov-report=html
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
2. **Dependencies**: Use Poetry for all dependency management
3. **Testing**: Maintain 90%+ test coverage
4. **Type Safety**: Use type hints throughout
5. **Performance**: Optimize for frequent operations (get_user_usage)

## 🌐 Environments

- **Development**: `api.dev.lingible.com`
- **Production**: `api.lingible.com`
- **API Gateway**: REST API with custom domain
- **Lambda Runtime**: Python 3.13