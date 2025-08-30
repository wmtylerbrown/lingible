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
├── src/
│   ├── models/              # Pydantic models (domain + API)
│   ├── services/            # Business logic layer
│   ├── repositories/        # Data access layer
│   ├── handlers/            # Lambda handlers
│   └── utils/               # Shared utilities
├── tests/                   # Unit and integration tests
├── infrastructure/          # AWS CDK infrastructure
├── requirements.txt         # Python dependencies
└── venv/                   # Virtual environment
```

## Setup

### Prerequisites

- Python 3.13+
- AWS CLI configured
- Node.js 18+ (for CDK)

### Local Development

1. **Create virtual environment:**
   ```bash
   python3.13 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Test setup:**
   ```bash
   python test_setup.py
   ```

4. **Run type checking:**
   ```bash
   mypy src/
   ```

5. **Format code:**
   ```bash
   black src/
   ```

## Usage Limits

- **Free Tier**: 10 translations/month
- **Premium Tier**: 100 translations/month
- **Text Length**: Max 1000 characters per translation

## API Endpoints

- `POST /api/translate` - Translate text
- `GET /api/translations/{id}` - Get translation status
- `GET /api/history` - Get user's translation history
- `GET /api/usage` - Get user's usage statistics

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

All code is strictly typed and follows Python best practices.
