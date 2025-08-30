# Technical Context - Lingible

## 🏗 **Architecture Overview**

### **Serverless Backend Architecture:**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Mobile App    │    │   Web Client    │    │   Third Party   │
│   (iOS/Android) │    │   (Future)      │    │   Integrations  │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │    API Gateway            │
                    │  (REST API + Authorizer)  │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │    Lambda Functions       │
                    │  (13 Handlers)            │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │    Service Layer          │
                    │  (Business Logic)         │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │    Repository Layer       │
                    │  (Data Access)            │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │    DynamoDB               │
                    │  (Single-Table Design)    │
                    └───────────────────────────┘
```

## 🔧 **Technology Stack**

### **Backend Runtime:**
- **Language**: Python 3.13
- **Framework**: AWS Lambda (serverless)
- **Type Safety**: Comprehensive type hints with mypy
- **Code Quality**: Black (formatting), flake8 (linting)

### **Infrastructure:**
- **IaC**: AWS CDK with TypeScript
- **Environment**: Separate dev/prod environments
- **Resource Naming**: `lingible-{service}-{environment}` pattern
- **Deployment**: Automated deployment scripts

### **Database:**
- **Primary**: DynamoDB with single-table design
- **Tables**:
  - `lingible-users-{env}` (users, subscriptions, usage)
  - `lingible-translations-{env}` (translation history)
- **Access Patterns**: Optimized for user-centric queries

### **Authentication & Security:**
- **Identity Provider**: AWS Cognito
- **External Auth**: Apple Identity Provider
- **API Security**: JWT-based authentication
- **Secrets**: AWS Secrets Manager for sensitive data

### **AI/ML Services:**
- **Translation**: AWS Bedrock (Claude 3 Sonnet)
- **Model**: `anthropic.claude-3-sonnet-20240229-v1:0`
- **Context**: GenZ language pattern recognition
- **Confidence**: Translation confidence scoring

## 📁 **Code Organization**

### **Project Structure:**
```
backend/
├── src/
│   ├── handlers/           # Lambda function handlers
│   │   ├── translate_api/  # Translation API
│   │   ├── user_profile_api/ # User management
│   │   ├── user_usage_api/ # Usage tracking
│   │   ├── translation_history_api/ # History management
│   │   ├── health_api/     # Health checks
│   │   ├── apple_webhook/  # App Store webhooks
│   │   ├── cognito_*_*/    # Cognito triggers
│   │   ├── user_data_cleanup/ # Data cleanup
│   │   └── authorizer/     # API Gateway authorizer
│   ├── models/             # Pydantic data models
│   ├── services/           # Business logic layer
│   ├── repositories/       # Data access layer
│   └── utils/              # Shared utilities
├── tests/                  # Comprehensive test suite
├── infrastructure/         # AWS CDK infrastructure
└── requirements.txt        # Dependencies
```

### **Handler Organization:**
- **Independent Deployment**: Each handler in its own directory
- **Shared Dependencies**: Common requirements at handler level
- **Modular Design**: Easy to deploy and maintain individually

## 🧪 **Testing Architecture**

### **Test-Driven Development (TDD):**
- **Mandatory Workflow**: Red-Green-Refactor for all development
- **Coverage Requirements**: 90% minimum, 100% for critical logic
- **Test Categories**: Unit, Integration, Model, Service, Repository, Handler

### **Test Infrastructure:**
- **Framework**: Pytest with comprehensive fixtures
- **AWS Mocking**: Moto for DynamoDB, Cognito, Secrets Manager
- **Coverage**: pytest-cov with HTML and terminal reports
- **Execution**: Custom test runner with multiple options

### **Test Organization:**
```
tests/
├── conftest.py           # Shared fixtures and configuration
├── test_models.py        # Pydantic model tests
├── test_services.py      # Business logic tests
├── test_repositories.py  # Data access tests
├── test_utils.py         # Utility function tests
├── test_handlers.py      # Lambda handler tests
└── README.md            # Test documentation
```

## 🔒 **Security Implementation**

### **Authentication Flow:**
1. **User Authentication**: Apple Sign-In via Cognito
2. **Token Generation**: JWT tokens with user context
3. **API Authorization**: API Gateway authorizer validates tokens
4. **Context Injection**: User context passed to Lambda functions

### **Data Protection:**
- **Encryption**: AES-256 encryption at rest and in transit
- **IAM Policies**: Least privilege access controls
- **Secrets Management**: AWS Secrets Manager for credentials
- **Audit Logging**: Comprehensive security event logging

### **API Security:**
- **CORS Configuration**: Proper cross-origin resource sharing
- **Rate Limiting**: API Gateway rate limiting
- **Input Validation**: Pydantic model validation
- **Error Handling**: Secure error responses without data leakage

## 📊 **Performance & Scalability**

### **Serverless Benefits:**
- **Auto-scaling**: Lambda functions scale automatically
- **Cost Efficiency**: Pay-per-use pricing model
- **High Availability**: Multi-AZ deployment
- **Cold Start Optimization**: Efficient function design

### **Database Optimization:**
- **Single-Table Design**: Efficient DynamoDB access patterns
- **Partition Key Strategy**: User-centric data distribution
- **GSI Optimization**: Optimized for common query patterns
- **TTL Management**: Automatic data expiration

### **Caching Strategy:**
- **DynamoDB DAX**: Read performance optimization
- **Lambda Layer Caching**: Shared dependency caching
- **API Gateway Caching**: Response caching for static data

## 🔄 **Data Flow**

### **Translation Request Flow:**
1. **Client Request**: Mobile app sends translation request
2. **API Gateway**: Routes to appropriate Lambda function
3. **Authorization**: JWT token validation
4. **Business Logic**: Service layer processes request
5. **AI Translation**: AWS Bedrock generates translation
6. **Data Storage**: Premium users get translation history
7. **Response**: Formatted response returned to client

### **User Management Flow:**
1. **Authentication**: Apple Sign-In via Cognito
2. **User Creation**: Cognito trigger creates user profile
3. **Usage Tracking**: Real-time usage monitoring
4. **Subscription Management**: App Store receipt validation
5. **Data Cleanup**: Cognito trigger handles user deletion

## 🚀 **Deployment Strategy**

### **Environment Separation:**
- **Development**: `lingible-dev` stack with `-dev` suffix
- **Production**: `lingible-prod` stack with `-prod` suffix
- **Resource Isolation**: Complete separation of environments
- **Configuration Management**: Environment-specific settings

### **Deployment Process:**
1. **Infrastructure**: CDK deployment of AWS resources
2. **Application**: Lambda function deployment
3. **Configuration**: Environment-specific configuration
4. **Testing**: Automated testing and validation
5. **Monitoring**: CloudWatch setup and alerting

### **CI/CD Pipeline:**
- **Source Control**: Git with feature branch workflow
- **Quality Gates**: Pre-commit hooks and automated testing
- **Deployment**: Automated deployment with rollback capability
- **Monitoring**: Real-time monitoring and alerting

## 📈 **Monitoring & Observability**

### **CloudWatch Integration:**
- **Metrics**: Custom metrics for business KPIs
- **Logs**: Structured JSON logging for analysis
- **Alarms**: Automated alerting for critical issues
- **Dashboards**: Real-time monitoring dashboards

### **Application Monitoring:**
- **Performance**: Lambda function performance metrics
- **Errors**: Error tracking and alerting
- **Usage**: User behavior and usage analytics
- **Cost**: AWS resource cost monitoring

### **Business Metrics:**
- **Translation Volume**: Daily/monthly translation counts
- **User Engagement**: Active users and usage patterns
- **Conversion**: Free to premium conversion rates
- **Performance**: API response times and error rates

## 🔧 **Development Workflow**

### **TDD Process:**
1. **RED**: Write failing tests that describe desired behavior
2. **GREEN**: Write minimal code to make tests pass
3. **REFACTOR**: Clean up code while keeping tests green

### **Quality Gates:**
- **Pre-commit**: Automated tests, formatting, and linting
- **Code Review**: Mandatory review with test coverage requirements
- **Integration Testing**: End-to-end testing for all features
- **Performance Testing**: Load testing for critical paths

### **Development Commands:**
```bash
# Run tests
python run_tests.py

# Run with coverage
python run_tests.py --coverage

# Code quality checks
black src/
flake8 src/
mypy src/

# Infrastructure deployment
cd infrastructure
python deploy-dev.py
```

## 🎯 **Current Technical Status**

### **✅ Completed:**
- **Core Architecture**: Serverless backend with clean architecture
- **API Implementation**: All core APIs implemented and tested
- **Security**: Authentication, authorization, and data protection
- **Testing**: Comprehensive test suite with TDD workflow
- **Infrastructure**: CDK infrastructure with environment separation
- **Monitoring**: CloudWatch integration and alerting

### **🔄 In Progress:**
- **Infrastructure Deployment**: Dev environment deployment
- **Integration Testing**: End-to-end testing validation
- **Performance Optimization**: Load testing and optimization

### **📋 Next Steps:**
- **Production Deployment**: Deploy to production environment
- **Monitoring Setup**: Complete monitoring and alerting
- **Documentation**: API documentation and deployment guides
- **Team Onboarding**: Developer setup and training

---

**Technical Status**: Ready for infrastructure deployment and production readiness phase. All core functionality implemented with comprehensive test coverage and TDD workflow established.
