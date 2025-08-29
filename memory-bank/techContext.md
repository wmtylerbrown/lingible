# Technical Context - GenZ Slang Translation App

## Technology Stack

### Core Technologies
- **Language**: Python 3.13
- **Framework**: AWS Lambda Powertools
- **Database**: Amazon DynamoDB
- **AI Service**: AWS Bedrock
- **Authentication**: AWS Cognito
- **Infrastructure**: AWS CDK (TypeScript)
- **API Gateway**: Amazon API Gateway (REST)

### Development Tools
- **Type Checking**: mypy with strict configuration
- **Linting**: flake8 for code quality
- **Formatting**: black for consistent code style
- **Version Control**: Git with comprehensive .gitignore
- **Memory Bank**: Cursor custom modes for structured development

## Architecture Overview

### Clean Architecture Implementation
```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (Handlers)                     │
├─────────────────────────────────────────────────────────────┤
│                  Business Logic (Services)                  │
├─────────────────────────────────────────────────────────────┤
│                Data Access (Repositories)                   │
├─────────────────────────────────────────────────────────────┤
│                    Infrastructure (AWS)                     │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

#### Handlers Layer
- **Purpose**: Lambda function entry points
- **Responsibilities**:
  - Event parsing and validation
  - Authentication and authorization
  - Request/response formatting
  - Error handling and logging
- **Patterns**:
  - `@event_parser` with typed models
  - `@handle_errors` decorator
  - Custom envelopes for event processing

#### Services Layer
- **Purpose**: Business logic and orchestration
- **Responsibilities**:
  - Domain-specific business rules
  - Service coordination
  - Validation and transformation
  - Usage tracking and rate limiting
- **Patterns**:
  - Dependency injection
  - Repository pattern integration
  - Comprehensive error handling

#### Repositories Layer
- **Purpose**: Data access abstraction
- **Responsibilities**:
  - Database operations
  - Query optimization
  - Data transformation
  - Caching strategies
- **Patterns**:
  - Repository pattern
  - Consistent partition key structure
  - Efficient DynamoDB patterns

#### Utilities Layer
- **Purpose**: Cross-cutting concerns
- **Responsibilities**:
  - AWS service management
  - Configuration management
  - Logging and tracing
  - Response formatting
  - Authentication utilities

## AWS Service Integration

### DynamoDB Design
- **Table Structure**: Single-table design with consistent partition keys
- **Partition Keys**:
  - `USER#{user_id}` - User data and profiles
  - `TRANSLATION#{translation_id}` - Translation history
  - `USAGE#LIMITS` - Usage tracking data
- **Sort Keys**: Timestamps and metadata for efficient querying
- **GSIs**: For querying by user, date ranges, and usage patterns

### Lambda Powertools Integration
- **Logger**: Structured logging with correlation IDs
- **Tracer**: AWS X-Ray integration for distributed tracing
- **Metrics**: Custom business metrics and CloudWatch integration
- **Parser**: Event parsing with Pydantic models
- **Config**: SSM Parameter Store integration for dynamic configuration

### AWS Bedrock Integration
- **Model**: Anthropic Claude for translation tasks
- **Prompt Engineering**: Optimized prompts for GenZ slang translation
- **Error Handling**: Graceful fallbacks and retry logic
- **Cost Optimization**: Efficient token usage and caching

## Data Models

### Core Models
- **BaseResponse**: Standardized API response format
- **User**: User profiles, tiers, and preferences
- **Translation**: Request/response models with metadata
- **UsageLimit**: Usage tracking and rate limiting
- **APIGatewayResponse**: Lambda response formatting

### Type Safety
- **Pydantic Models**: All data structures use Pydantic BaseModel
- **Strict Typing**: mypy configuration enforces strict type checking
- **Validation**: Field validators for data integrity
- **Serialization**: Automatic JSON serialization/deserialization

## Security & Authentication

### Cognito Integration
- **User Pool**: Managed user authentication
- **Token Validation**: JWT token verification
- **User Extraction**: Utility functions for user context
- **Authorization**: Role-based access control

### API Security
- **HTTPS**: All API endpoints use HTTPS
- **CORS**: Proper CORS configuration for mobile app
- **Rate Limiting**: Usage-based rate limiting
- **Input Validation**: Comprehensive request validation

## Performance & Scalability

### Lambda Optimization
- **Cold Start**: Minimized with efficient initialization
- **Memory**: Optimized memory allocation for cost/performance
- **Timeout**: Appropriate timeout configurations
- **Concurrency**: Auto-scaling based on demand

### DynamoDB Optimization
- **Partition Keys**: Even distribution across partitions
- **Query Patterns**: Optimized for common access patterns
- **Indexing**: Strategic GSI usage for efficient queries
- **Caching**: Application-level caching where appropriate

### Cost Optimization
- **Resource Sizing**: Right-sized Lambda functions
- **Database**: Efficient DynamO usage patterns
- **Monitoring**: Cost tracking and alerting
- **Caching**: Reduce redundant API calls

## Development Workflow

### Code Quality
- **Type Safety**: 100% typed codebase with mypy
- **Linting**: flake8 for code quality enforcement
- **Formatting**: black for consistent code style
- **Documentation**: Comprehensive docstrings and type hints

### Testing Strategy
- **Unit Tests**: Service and utility testing
- **Integration Tests**: Handler and repository testing
- **End-to-End Tests**: API endpoint testing
- **Performance Tests**: Load and stress testing

### Deployment Pipeline
- **Infrastructure**: CDK for infrastructure as code
- **CI/CD**: Automated testing and deployment
- **Environment**: Development, staging, production
- **Monitoring**: CloudWatch and custom metrics

## Error Handling & Observability

### Error Strategy
- **Exception Hierarchy**: Structured application exceptions
- **Error Codes**: Consistent error code system
- **HTTP Status**: Proper HTTP status code mapping
- **User Feedback**: Clear error messages for users

### Logging Strategy
- **Structured Logging**: JSON-formatted logs with correlation IDs
- **Business Events**: Key business events for analytics
- **Error Logging**: Comprehensive error tracking
- **Performance Logging**: Response time and resource usage

### Monitoring Strategy
- **Metrics**: Custom business and technical metrics
- **Alerts**: Proactive alerting for issues
- **Dashboards**: Operational dashboards
- **Tracing**: Distributed tracing for debugging

## Configuration Management

### SSM Parameter Store
- **Environment Variables**: Dynamic configuration
- **Feature Flags**: Runtime feature toggles
- **API Keys**: Secure credential management
- **Usage Limits**: Configurable rate limits

### Environment Management
- **Development**: Local development configuration
- **Staging**: Pre-production testing environment
- **Production**: Live environment configuration
- **Secrets**: Secure secret management
