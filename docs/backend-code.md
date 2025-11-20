# Backend Code Structure

This document describes the structure and patterns used in the Lingible backend codebase.

## Directory Structure

```
backend/lambda/src/
├── handlers/          # Lambda entry points
│   ├── *_api/        # API handlers (synchronous)
│   ├── *_async/      # Async handlers (SNS-triggered)
│   └── *_trigger/    # Cognito triggers
├── services/         # Business logic layer
├── repositories/     # Data access layer
├── models/           # Pydantic models
└── utils/            # Shared utilities
```

## AWS Services Management

### Centralized Service Manager

**Location**: `src/utils/aws_services.py`

**Pattern**: Singleton with lazy initialization

```python
class AWSServices:
    def __init__(self):
        self._dynamodb_resource = None
        self._cognito_client = None
        # ... other clients

    @property
    def dynamodb_resource(self):
        if self._dynamodb_resource is None:
            self._dynamodb_resource = boto3.resource('dynamodb')
        return self._dynamodb_resource
```

**Usage**:
```python
from utils.aws_services import aws_services

table = aws_services.dynamodb_resource.Table('users-table')
client = aws_services.cognito_client
```

**Benefits**:
- Lazy initialization (only creates clients when needed)
- Reduces cold start time
- Single point of configuration
- Easy to mock in tests

## Repository Pattern

### Purpose

Repositories abstract DynamoDB access and provide type-safe interfaces for data operations.

### Structure

```python
class UserRepository:
    def __init__(self):
        self.table = aws_services.dynamodb_resource.Table(os.environ['USERS_TABLE'])

    def get_user(self, user_id: str) -> User:
        """Get user by ID. Raises UserNotFoundError if not found."""
        response = self.table.get_item(Key={'PK': f'USER#{user_id}', 'SK': 'PROFILE'})
        if 'Item' not in response:
            raise UserNotFoundError(f"User {user_id} not found")
        return self._item_to_user(response['Item'])

    def create_user(self, user: User) -> User:
        """Create new user. Raises SystemError on failure."""
        item = self._user_to_item(user)
        try:
            self.table.put_item(Item=item, ConditionExpression='attribute_not_exists(PK)')
            return user
        except Exception as e:
            raise SystemError(f"Failed to create user: {e}")

    def _user_to_item(self, user: User) -> dict:
        """Convert User model to DynamoDB item."""
        # Conversion logic

    def _item_to_user(self, item: dict) -> User:
        """Convert DynamoDB item to User model."""
        # Conversion logic
```

### Repository Responsibilities

- **Data Access**: All DynamoDB operations
- **Type Conversion**: Model ↔ DynamoDB item conversion
- **Error Handling**: Raise domain-specific exceptions
- **Index Usage**: Query appropriate GSIs for access patterns

See `docs/repositories.md` for detailed repository responsibilities.

## Service Layer

### Purpose

Services contain business logic and orchestrate repository calls.

### Structure

```python
class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
        self.config = ConfigService()

    def get_user(self, user_id: str) -> UserResponse:
        """Get user profile as API response."""
        user = self.user_repo.get_user(user_id)
        return user.to_api_response()

    def upgrade_user_tier(self, user_id: str, subscription: UserSubscription) -> UpgradeResponse:
        """Upgrade user tier based on subscription."""
        user = self.user_repo.get_user(user_id)

        # Business logic
        if user.tier == UserTier.PREMIUM:
            raise ValidationError("User already premium")

        # Update user
        user.tier = UserTier.PREMIUM
        self.user_repo.update_user(user)

        return UpgradeResponse(user_id=user_id, new_tier=UserTier.PREMIUM)
```

### Service Responsibilities

- **Business Logic**: Validation, calculations, orchestration
- **Repository Coordination**: Call multiple repositories as needed
- **External Services**: Integrate with AWS services, third-party APIs
- **Error Handling**: Convert repository exceptions to API errors
- **Response Transformation**: Convert domain models to API responses

## Handler Layer

### Purpose

Handlers are Lambda entry points that integrate with API Gateway.

### Structure

```python
from utils.handler_authorization import HandlerAuthorization
from utils.event_parser import parse_api_event
from services.user_service import UserService
from repositories.user_repository import UserRepository

@HandlerAuthorization.require_user
def handler(event, context):
    """GET /user/profile"""
    try:
        # Parse request
        user_id = event.requestContext.authorizer.claims['sub']

        # Initialize services
        user_repo = UserRepository()
        user_service = UserService(user_repo)

        # Call service
        result = user_service.get_user(user_id)

        # Return response
        return create_success_response(result)
    except UserNotFoundError as e:
        return create_error_response(404, str(e))
    except Exception as e:
        logger.error("Unexpected error", extra={"error": str(e)})
        return create_error_response(500, "Internal server error")
```

### Handler Responsibilities

- **Request Parsing**: Extract data from API Gateway event
- **Authorization**: Extract user context from authorizer
- **Service Initialization**: Create repository and service instances
- **Response Formatting**: Create API Gateway-compatible responses
- **Error Handling**: Catch exceptions and return appropriate HTTP status codes

## Model Layer

### Purpose

Pydantic models provide type safety and validation.

### Base Model

**Location**: `src/models/base.py`

```python
class LingibleBaseModel(BaseModel):
    """Base model with automatic enum serialization."""

    @classmethod
    def _serialize_value(cls, value: Any) -> Any:
        if isinstance(value, Enum):
            return str(value.value)  # Serialize enum to string value
        return value
```

### Model Structure

```python
class User(LingibleBaseModel):
    user_id: str
    email: str
    tier: UserTier  # Enum
    status: UserStatus  # Enum
    created_at: datetime
    updated_at: datetime

    def to_api_response(self) -> UserResponse:
        """Convert to API response model."""
        return UserResponse(
            user_id=self.user_id,
            email=self.email,
            tier=str(self.tier),
            status=str(self.status),
            created_at=self.created_at.isoformat(),
            updated_at=self.updated_at.isoformat()
        )
```

### Model Responsibilities

- **Type Safety**: Strong typing for all data structures
- **Validation**: Pydantic validators for data integrity
- **Serialization**: Automatic JSON serialization with enum handling
- **API Transformation**: `to_api_response()` methods for API contracts

## Configuration Service

### Purpose

Centralized configuration management for secrets and environment variables.

### Structure

**Location**: `src/utils/config.py`

```python
class ConfigService:
    def __init__(self):
        self.environment = os.environ.get('ENVIRONMENT', 'dev')

    def get_config(self, config_type: Type[T]) -> T:
        """Get configuration object of specified type."""
        if config_type == AppleConfig:
            # Retrieve from SSM Parameter Store
            private_key = self._get_ssm_secure_parameter(
                f"/lingible/{self.environment}/secrets/apple-iap-private-key"
            )
            return AppleConfig(private_key=private_key, ...)
```

### Configuration Types

- **AppleConfig**: Apple IAP credentials (SSM SecureString)
- **SlangValidationConfig**: Tavily API key (SSM SecureString)
- **Environment Variables**: Table names, log levels, feature flags

## Error Handling

### Exception Hierarchy

```python
# Domain exceptions
class UserNotFoundError(Exception):
    pass

class ValidationError(Exception):
    pass

class SystemError(Exception):
    pass
```

### Error Handling Pattern

**Repositories**: Raise domain exceptions
```python
def get_user(self, user_id: str) -> User:
    if not found:
        raise UserNotFoundError(f"User {user_id} not found")
```

**Services**: Convert to API errors
```python
def get_user(self, user_id: str) -> UserResponse:
    try:
        user = self.user_repo.get_user(user_id)
    except UserNotFoundError:
        raise NotFoundError("User not found")
```

**Handlers**: Return HTTP responses
```python
try:
    result = service.get_user(user_id)
    return create_success_response(result)
except NotFoundError as e:
    return create_error_response(404, str(e))
```

## Testing Patterns

### Fixtures

**Location**: `tests_v2/conftest.py`

```python
@pytest.fixture
def users_table(moto_dynamodb):
    """Create users table schema for tests."""
    table_name = "test-users-table"
    os.environ["USERS_TABLE"] = table_name

    # Create table with moto
    # Set up aws_services to use moto client
    return table_name
```

### Mocking AWS Services

```python
from moto import mock_dynamodb

@mock_dynamodb
def test_get_user(users_table):
    repo = UserRepository()
    user = repo.get_user("user_123")
    assert user.user_id == "user_123"
```

### Service Testing

```python
def test_user_service_get_user(mock_user_repo):
    mock_user_repo.get_user.return_value = User(user_id="user_123", ...)

    service = UserService(mock_user_repo)
    result = service.get_user("user_123")

    assert result.user_id == "user_123"
    mock_user_repo.get_user.assert_called_once_with("user_123")
```

## Code Organization Principles

1. **Separation of Concerns**: Handlers → Services → Repositories
2. **Dependency Injection**: Services receive repositories as constructor args
3. **Type Safety**: Strong typing throughout (Pydantic models, type hints)
4. **Error Handling**: Domain exceptions → API errors → HTTP responses
5. **Testability**: Easy to mock dependencies, use real models in tests
6. **Reusability**: Shared utilities, common patterns in base classes
