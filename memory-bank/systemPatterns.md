# System Patterns - Lingible

## Architectural Patterns

### Clean Architecture Implementation
- **Separation of Concerns**: Clear boundaries between handlers, services, repositories, and utilities
- **Dependency Inversion**: Services depend on repository interfaces, not concrete implementations
- **Single Responsibility**: Each component has a single, well-defined purpose
- **Testability**: All business logic is isolated and easily testable

### Repository Pattern
- **Abstract Data Access**: Repositories abstract database operations from business logic
- **Consistent Interface**: All repositories follow the same interface patterns
- **DynamoDB Optimization**: Single-table design with efficient partition key strategies
- **Error Handling**: Repository-level error handling with proper exception propagation

### Service Layer Pattern
- **Business Logic Encapsulation**: All business rules and workflows in service layer
- **Transaction Management**: Service methods handle multi-step operations
- **Validation**: Input validation and business rule enforcement
- **Orchestration**: Coordination between multiple repositories and external services

## Code Organization Patterns

### File Structure
```
src/
├── handlers/          # Lambda function entry points
├── services/          # Business logic layer
├── repositories/      # Data access layer
├── models/           # Pydantic data models
└── utils/            # Cross-cutting utilities
```

### Naming Conventions
- **Files**: snake_case (e.g., `user_service.py`, `translation_handler.py`)
- **Classes**: PascalCase (e.g., `UserService`, `TranslationHandler`)
- **Functions**: snake_case (e.g., `get_user_profile`, `translate_text`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_TRANSLATIONS_PER_DAY`)
- **Variables**: snake_case (e.g., `user_id`, `translation_result`)

### Import Organization
- **Standard Library**: Python standard library imports first
- **Third-Party**: External package imports second
- **Local Imports**: Project-specific imports last
- **Alphabetical Order**: Within each group, alphabetical ordering

## Handler Patterns

### Event Processing
- **Typed Events**: Use Pydantic models for event structure
- **Custom Envelopes**: Custom event parsing for type safety
- **Error Handling**: Centralized error handling with decorators
- **Response Formatting**: Consistent API response structure

### Authentication
- **Cognito Integration**: Extract user context from JWT tokens
- **Authorization**: Role-based access control
- **User Context**: Pass user information to business logic
- **Security**: Validate all user inputs and permissions

### Logging and Tracing
- **Structured Logging**: JSON-formatted logs with correlation IDs
- **Business Events**: Log key business operations for analytics
- **Error Tracking**: Comprehensive error logging with context
- **Performance Monitoring**: Response time and resource usage tracking

## Service Patterns

### Business Logic
- **Validation**: Input validation and business rule enforcement
- **Error Handling**: Proper exception handling and propagation
- **Transaction Management**: Multi-step operation coordination
- **Caching**: Strategic caching for performance optimization

### External Service Integration
- **AWS Services**: Centralized AWS service management
- **Error Handling**: Graceful fallbacks and retry logic
- **Configuration**: Dynamic configuration via SSM Parameter Store
- **Monitoring**: Service health and performance tracking

### Usage Tracking
- **Rate Limiting**: Tier-based usage limits and enforcement
- **Metrics**: Business metrics for analytics and monitoring
- **Audit Trail**: Comprehensive audit logging
- **User Experience**: Clear feedback on usage limits

## Repository Patterns

### DynamoDB Design
- **Single Table**: Efficient single-table design with consistent patterns
- **Partition Keys**: Strategic partition key design for even distribution
- **Sort Keys**: Efficient querying with sort key optimization
- **GSIs**: Global secondary indexes for alternative access patterns

### Data Access
- **CRUD Operations**: Standard create, read, update, delete operations
- **Query Optimization**: Efficient query patterns for common use cases
- **Batch Operations**: Batch processing for performance
- **Error Handling**: Proper error handling and retry logic

## API Management Patterns

### Shared API Contract
- **Single Source of Truth**: All API definitions in shared files
- **OpenAPI Specification**: `shared/api/openapi/lingible-api.yaml` defines the complete API contract
- **Cross-Platform Consistency**: Shared definitions ensure consistency across backend, iOS, and Android

### API Change Management
- **MANDATORY**: Any API changes require updates to shared files
- **OpenAPI Updates**: Endpoint definitions, schemas, examples, error responses
- **Type Updates**: Interface definitions, constants, type exports
- **Configuration Updates**: API-related constants in shared config
- **Verification**: Test config loader and validate OpenAPI spec

### API Documentation
- **Living Documentation**: OpenAPI spec serves as living API documentation
- **Code Generation**: Shared types enable code generation for client SDKs
- **Testing**: Shared types ensure consistent testing across platforms
- **Version Control**: API changes tracked in version control with shared files

### Caching Strategy
- **Application Cache**: In-memory caching for frequently accessed data
- **TTL Management**: Appropriate time-to-live for cached data
- **Cache Invalidation**: Proper cache invalidation strategies
- **Performance Monitoring**: Cache hit/miss ratio tracking

## Error Handling Patterns

### Exception Hierarchy
- **Base Exceptions**: Common base exception classes
- **Domain Exceptions**: Business-specific exception types
- **HTTP Mapping**: Proper HTTP status code mapping
- **User Feedback**: Clear, actionable error messages

### Error Propagation
- **Service Layer**: Business logic error handling
- **Handler Layer**: API-level error handling
- **Repository Layer**: Data access error handling
- **Utility Layer**: Cross-cutting error handling

### Error Logging
- **Structured Logs**: JSON-formatted error logs
- **Context Information**: Relevant context for debugging
- **Correlation IDs**: Request correlation for tracing
- **Error Classification**: Error categorization for monitoring

## Configuration Patterns

### Environment Management
- **SSM Parameter Store**: Centralized configuration management
- **Environment Variables**: Runtime configuration
- **Feature Flags**: Runtime feature toggles
- **Secrets Management**: Secure credential management

### Dynamic Configuration
- **Runtime Updates**: Configuration changes without deployment
- **Validation**: Configuration validation and defaults
- **Caching**: Configuration caching for performance
- **Monitoring**: Configuration change tracking

## Testing Patterns

### Unit Testing
- **Service Testing**: Business logic unit tests
- **Repository Testing**: Data access layer testing
- **Utility Testing**: Cross-cutting concern testing
- **Mocking**: Proper mocking of external dependencies

### Integration Testing
- **Handler Testing**: End-to-end handler testing
- **Database Testing**: Repository integration testing
- **External Service Testing**: AWS service integration testing
- **Error Scenario Testing**: Error handling validation

### Test Organization
- **Test Structure**: Mirror source code structure
- **Test Naming**: Descriptive test method names
- **Test Data**: Consistent test data management
- **Test Utilities**: Reusable test utilities and fixtures

## Performance Patterns

### Lambda Optimization
- **Cold Start**: Efficient initialization and lazy loading
- **Memory Management**: Optimal memory allocation
- **Timeout Configuration**: Appropriate timeout settings
- **Concurrency**: Auto-scaling configuration

### Database Optimization
- **Query Patterns**: Efficient DynamoDB query patterns
- **Indexing**: Strategic index usage
- **Batch Operations**: Batch processing for efficiency
- **Connection Management**: Efficient connection handling

### Caching Strategy
- **Application Cache**: In-memory caching
- **Database Cache**: DynamoDB DAX for read-heavy workloads
- **CDN**: Content delivery network for static assets
- **Cache Invalidation**: Proper cache invalidation

## Security Patterns

### Authentication
- **JWT Validation**: Proper JWT token validation
- **User Context**: Secure user context extraction
- **Authorization**: Role-based access control
- **Session Management**: Secure session handling

### Data Protection
- **Input Validation**: Comprehensive input validation
- **Output Encoding**: Proper output encoding
- **SQL Injection**: Parameterized queries
- **XSS Prevention**: Cross-site scripting prevention

### API Security
- **HTTPS**: All API endpoints use HTTPS
- **CORS**: Proper CORS configuration
- **Rate Limiting**: Usage-based rate limiting
- **Request Validation**: Comprehensive request validation

## Backend Development Patterns

### **CRITICAL: Virtual Environment & Deployment Rules**

#### **Virtual Environment Usage:**
- **MANDATORY**: Always activate the project virtual environment before running any Python commands
- **Location**: Project root `.venv` directory (`/Users/tyler/mobile-app-aws-backend/.venv`)
- **Activation**: `source .venv/bin/activate` from project root
- **Poetry Commands**: Always run `poetry` commands from `backend/lambda/` directory with activated venv

#### **Backend Deployment Process:**
- **MANDATORY**: Always use `package.json` scripts for backend deployment, never direct CDK commands
- **Location**: `backend/infrastructure/package.json`
- **Commands**:
  - `npm run deploy:dev` (development deployment)
  - `npm run deploy:prod` (production deployment)
  - `npm run build` (build Lambda packages)
- **Why**: Package.json scripts handle proper build processes, environment configuration, and deployment order

#### **Dependency Management:**
- **Installation**: `cd backend/lambda && poetry lock && poetry install` (with activated venv)
- **Virtual Environment**: Project uses `.venv` at project root, NOT nested venvs
- **Python Path**: Always set `PYTHONPATH=backend/lambda/src` for local development

### **Common Deployment Mistakes to Avoid:**
- ❌ Running commands without activated virtual environment
- ❌ Using direct `cdk deploy` instead of `npm run deploy:*`
- ❌ Running Poetry commands from wrong directory
- ❌ Forgetting to run `poetry lock` after dependency changes

## iOS Development Patterns

### Build Process
- **CRITICAL**: Always use custom build script `./build_app.sh` instead of Xcode build button (⌘+B)
- **Environment Management**: Script handles dev/prod environment switching automatically
- **Configuration Safety**: Prevents wrong environment configurations and ensures proper `amplify_outputs.json` files
- **Usage**: `./build_app.sh dev` (development), `./build_app.sh prod` (production), `./build_app.sh both` (both environments)
- **Location**: `/Users/tyler/mobile-app-aws-backend/ios/Lingible/build_app.sh`

### Build Script Benefits
- **Consistency**: Same build process every time across environments
- **Environment Safety**: Automatic switching between dev/prod configurations
- **Bundle ID Management**: Correct bundle identifiers for each environment
- **Post-Build Cleanup**: Restores development configuration for testing
- **Validation**: Built-in error checking and detailed build reporting
