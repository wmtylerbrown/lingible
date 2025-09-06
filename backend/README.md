# Lingible Backend

A serverless backend for translating GenZ slang to English and vice versa using AWS Bedrock.

## Architecture

- **AWS Lambda** - Serverless compute
- **API Gateway** - REST API endpoints
- **DynamoDB** - Data storage
- **AWS Cognito** - User authentication
- **AWS Bedrock** - AI translation service
- **AWS CDK** - Infrastructure as Code

## Project Structure

```
backend/
├── lambda/                  # Python Lambda functions
│   ├── src/                # Lambda function source code
│   │   ├── models/         # Pydantic models (domain + API)
│   │   ├── services/       # Business logic layer
│   │   ├── repositories/   # Data access layer
│   │   ├── handlers/       # Lambda handlers
│   │   └── utils/          # Shared utilities
│   ├── tests/              # Unit and integration tests
│   ├── requirements.txt    # Python dependencies
│   ├── pytest.ini         # Pytest configuration
│   ├── run_tests.py       # Test execution script
│   └── README.md          # Lambda development guide
├── infrastructure/         # AWS CDK infrastructure
│   ├── app.ts             # CDK app entry point
│   ├── constructs/        # CDK constructs
│   ├── stacks/            # CDK stacks
│   ├── scripts/           # Infrastructure scripts
│   ├── package.json       # Node.js dependencies
│   └── README.md          # Infrastructure guide
└── docs/                  # Backend documentation
```

## Quick Start

### Lambda Development
```bash
# Navigate to Lambda code
cd backend/lambda

# Install Python dependencies
pip install -r requirements.txt

# Run tests
python run_tests.py

# Run with coverage
python run_tests.py --coverage
```

### Infrastructure Development
```bash
# Navigate to infrastructure
cd backend/infrastructure

# Install Node.js dependencies
npm install

# Build TypeScript
npm run build

# Deploy to dev environment
npm run deploy:dev
```

## Setup

### Prerequisites

- Python 3.13+ (for Lambda functions)
- Node.js 18+ (for CDK infrastructure)
- AWS CLI configured

### Local Development

1. **Lambda Functions:**
   ```bash
   cd backend/lambda
   pip install -r requirements.txt
   python run_tests.py
   ```

2. **Infrastructure:**
   ```bash
   cd backend/infrastructure
   npm install
   npm run build
   ```

3. **Type checking:**
   ```bash
   # Python
   cd backend/lambda
   mypy src/

   # TypeScript
   cd backend/infrastructure
   npm run lint
   ```

4. **Format code:**
   ```bash
   # Python
   cd backend/lambda
   black src/

   # TypeScript
   cd backend/infrastructure
   npm run lint:fix
   ```

## Usage Limits

- **Free Tier**: 10 translations/month
- **Premium Tier**: 100 translations/month
- **Text Length**: Max 1000 characters per translation

## API Endpoints

- `POST /translate` - Translate text
- `GET /translations` - Get translation history (premium)
- `DELETE /translations/{id}` - Delete specific translation
- `DELETE /translations` - Clear all translations
- `GET /user/profile` - Get user profile
- `GET /user/usage` - Get usage statistics
- `POST /user/upgrade` - Upgrade user subscription
- `GET /health` - Health check

## Development

The codebase follows a clean architecture pattern:

1. **Models** - Data structures and validation
2. **Services** - Business logic and rules
3. **Repositories** - Data access and persistence
4. **Handlers** - HTTP request/response handling

### AWS Services Efficiency

We use a centralized AWS services manager for optimal Lambda performance:

- **Singleton Pattern**: Each boto3 client is created only once per Lambda container
- **Lazy Initialization**: Services are only created when first accessed
- **Shared Instances**: All handlers and repositories share the same client instances
- **Reduced Cold Start**: Faster Lambda startup times

```python
from src.utils.aws_services import aws_services

# Efficient access to AWS services
cognito_client = aws_services.cognito_client
dynamodb_resource = aws_services.dynamodb_resource
bedrock_client = aws_services.bedrock_client
```

See [AWS Services Efficiency Guide](docs/aws_services_efficiency.md) for detailed documentation.

### Lambda Configuration

Our Lambda functions are configured with:

- **Memory Allocation**: 512 MB for all functions (standard configuration)
- **Runtime**: Python 3.13
- **Timeout**: 30 seconds
- **Cold Start Behavior**: Standard AWS Lambda cold start behavior

See [Lambda Optimization Guide](docs/lambda-optimization.md) for detailed documentation and optimization history.

## Testing

### Lambda Functions
```bash
cd backend/lambda

# Run all tests
python run_tests.py

# Run specific test types
python run_tests.py --type unit
python run_tests.py --type integration
python run_tests.py --type handler

# Run with coverage
python run_tests.py --coverage
```

### Infrastructure
```bash
cd backend/infrastructure

# Run tests
npm test

# Run with coverage
npm run test:coverage
```

## Deployment

### Development Environment
```bash
cd backend/infrastructure

# Deploy hosted zones first
npm run deploy:hosted-zones:dev

# Deploy full stack
npm run deploy:dev
```

### Production Environment
```bash
cd backend/infrastructure

# Deploy hosted zones first
npm run deploy:hosted-zones:prod

# Deploy full stack
npm run deploy:prod
```

## Code Quality

All code is strictly typed and follows best practices:

- **Python**: Type hints, mypy, flake8, black
- **TypeScript**: ESLint, Prettier, strict mode
- **Testing**: 90%+ coverage requirement
- **TDD**: Mandatory test-driven development workflow

## Related Documentation

- [Lambda Functions](lambda/README.md) - Python Lambda development guide
- [Infrastructure](infrastructure/README.md) - CDK infrastructure guide
- [API Documentation](docs/) - API documentation and guides
- [Project Overview](../../README.md) - Main project documentation
