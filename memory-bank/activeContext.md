# Active Context - Lingible

## Current Focus: Infrastructure Deployment & Production Readiness

### ✅ **COMPLETED: Test-Driven Development (TDD) Rule Implementation (2024-12-19)**
- **Mandatory TDD Workflow**: Red-Green-Refactor process for all backend development
- **Test Coverage Standards**: 90% minimum for new code, 100% for critical business logic
- **Quality Enforcement**: Code review rejection for missing tests, pre-commit requirements
- **Comprehensive Guidelines**: Complete TDD rule document with examples and best practices

### ✅ **COMPLETED: Comprehensive Test Suite Creation (2024-12-19)**
- **Full Test Coverage**: Unit tests for models, services, repositories, utilities, and handlers
- **Test Infrastructure**: Pytest, `conftest.py` for fixtures, `run_tests.py` for execution
- **AWS Mocking**: Using `moto` for isolated testing of AWS interactions
- **Documentation**: `tests/README.md` provides detailed guidance
- **Coverage Reporting**: HTML and terminal coverage reports with 90%+ coverage targets

### ✅ **COMPLETED: Lingible Rebranding (2024-12-19)**
- **Full Codebase Rebranding**: Successfully rebranded from "GenZ Translation App" to "Lingible"
- **Bundle ID**: Updated to `com.lingible.lingible` for app stores
- **Infrastructure**: All AWS resources now use "lingible-" prefix
- **Documentation**: All files updated with new branding
- **Configuration**: All app references updated

### ✅ **COMPLETED: AWS CDK Infrastructure Setup (2024-12-19)**
- **Environment-Based Deployment**: CDK infrastructure supports dev/prod environments
- **Resource Naming**: All resources properly namespaced (e.g., `lingible-users-dev`, `lingible-api-prod`)
- **Deployment Scripts**: `deploy-dev.py` and `deploy-prod.py` for streamlined deployments
- **Security**: Apple Identity Provider integration with AWS Secrets Manager for private key storage
- **Monitoring**: CloudWatch metrics, logging, and alerting configured

### ✅ **COMPLETED: Lambda Layer Architecture & CDK Docker Bundling (2024-12-19)**
- **Dual Layer Strategy**: Separate dependencies layer (Python packages) and shared code layer (custom code)
- **CDK Docker Bundling**: Replaced custom build scripts with CDK's built-in Docker container bundling
- **Platform-Specific Dependencies**: Use `--platform manylinux2014_x86_64` for Lambda runtime compatibility
- **Resolved Import Issues**: Fixed persistent `pydantic_core._pydantic_core` errors through proper platform targeting
- **Container-Based Building**: Dependencies built in Python 3.13 containers matching Lambda runtime
- **Eliminated Platform Mismatches**: No more macOS-compiled packages causing Lambda import failures

### ✅ **COMPLETED: API Design & Implementation (2024-12-19)**
- **Translation APIs**: POST `/translate`, GET `/translations`, DELETE `/translations/{id}`, DELETE `/translations`
- **User Management**: GET `/user/profile`, GET `/user/usage`, POST `/user/upgrade`
- **System APIs**: GET `/health`
- **Premium Features**: Translation history storage for premium users only
- **Error Handling**: Standardized custom exceptions with proper HTTP status codes

### ✅ **COMPLETED: Authorization & Security (2024-12-19)**
- **API Gateway Authorizer**: Separate Lambda function for JWT validation
- **Cognito Integration**: Apple Identity Provider for external authentication
- **Security Best Practices**: Private key storage in AWS Secrets Manager
- **Authorization Decorators**: Lambda-level authorization with user context injection

### ✅ **COMPLETED: Error Handling & Logging (2024-12-19)**
- **Custom Exception Hierarchy**: `AppException` base with specialized subclasses
- **Standardized Error Responses**: Consistent API error structures with error codes
- **Smart Logging**: Cost-optimized logging strategy with `SmartLogger`
- **Error Codes**: Enum-based error codes for consistent error handling

### ✅ **COMPLETED: Data Models & Architecture (2024-12-19)**
- **Pydantic Models**: Type-safe data structures for all entities
- **Single-Table Design**: DynamoDB design pattern for efficient data access
- **Event Models**: Specialized models for different API patterns
- **Clean Architecture**: Separation of concerns with service and repository layers

### ✅ **COMPLETED: Receipt Validation Service (2024-12-19)**
- **Apple Store Integration**: Direct HTTP calls to Apple's verification API
- **Google Play Integration**: Service account-based verification
- **Security**: Secure credential storage and validation
- **Error Handling**: Comprehensive error handling for validation failures

### ✅ **COMPLETED: User Management & Cleanup (2024-12-19)**
- **Cognito Triggers**: Pre-user deletion handler for data cleanup
- **Background Cleanup**: Orchestrated user data cleanup via dedicated handler
- **Soft Deletion**: Marking user status as `CANCELLED` before hard deletion
- **Data Integrity**: Ensuring all user data is properly cleaned up

### ✅ **COMPLETED: Code Quality & Standards (2024-12-19)**
- **Pre-commit Hooks**: Black, flake8, mypy, and trailing whitespace checks
- **Type Safety**: Comprehensive type hints throughout the codebase
- **Code Organization**: Modular handler structure with independent deployment
- **Documentation**: Comprehensive inline documentation and README files

### 🔄 **IN PROGRESS: Translation API Debugging (2024-12-31)**
- **Authentication System**: ✅ Working perfectly with fresh JWT tokens from Cognito
- **Enum Serialization Issues**: ✅ Completely resolved across all repositories
  - Fixed `UserTier` enum serialization in `user_repository.py`
  - Fixed `TranslationDirection` enum serialization in `translation_repository.py`
  - Fixed `SubscriptionProvider` and `SubscriptionStatus` enum serialization in `subscription_repository.py`
- **Configuration Management**: ✅ Bedrock configuration loading correctly
- **IAM Permissions**: ✅ Added `bedrock:InvokeModel` permission to Lambda function
- **Model Access**: ✅ Updated to accessible Bedrock model (`anthropic.claude-3-5-sonnet-20241022-v2:0`)
- **SSM Parameter Store**: ✅ Updated with correct model configuration
- **Current Blocker**: "User is not authorized to access this resource with an explicit deny" - investigating API Gateway resource policies

### 🎯 **CURRENT PRIORITIES:**

#### **1. Translation API Debugging & Production Readiness**
- **Current Status**: 95% complete - only final authorization issue remaining
- **Authentication**: ✅ Working perfectly with fresh JWT tokens from Cognito
- **Enum Serialization**: ✅ Completely resolved across all repositories
- **Configuration**: ✅ Bedrock configuration loading correctly
- **IAM Permissions**: ✅ Added Bedrock permissions to Lambda function
- **Model Access**: ✅ Updated to accessible Bedrock model
- **Current Blocker**: "User is not authorized to access this resource with an explicit deny"

#### **2. Infrastructure Deployment & Lambda Layer Resolution**
- **Environment-Based Deployment**: CDK infrastructure supports dev/prod environments
- **Resource Naming**: All resources properly namespaced (e.g., `lingible-users-dev`, `lingible-api-prod`)
- **Deployment Scripts**: `deploy-dev.py` and `deploy-prod.py` for streamlined deployments
- **Lambda Layer Architecture**: Successfully implemented with CDK Docker bundling
- **Import Structure Resolution**: Need to fix relative vs absolute imports for local development

#### **2. Security Enhancements**
- **Apple Identity Provider Private Key**: Secure storage in AWS Secrets Manager
- **API Gateway Security**: Proper CORS configuration and rate limiting
- **Monitoring & Alerting**: Security event monitoring and alerting

#### **3. Production Readiness**
- **Performance Optimization**: Lambda function optimization and cold start reduction
- **Monitoring & Observability**: CloudWatch dashboards and alerting
- **Cost Optimization**: Translation storage optimization and usage tracking
- **Disaster Recovery**: Backup strategies and recovery procedures

#### **4. Testing & Quality Assurance**
- **TDD Enforcement**: Mandatory test-driven development for all changes
- **Test Coverage**: Maintain 90%+ coverage for all new code
- **Integration Testing**: End-to-end testing for critical user flows
- **Performance Testing**: Load testing for API endpoints

#### **5. Development Environment & Import Resolution**
- **Lambda Layer Success**: Dependencies now working correctly in production
- **Import Structure Issue**: Relative imports in handlers need resolution for local development
- **PYTHONPATH Strategy**: Planning to use package.json scripts with PYTHONPATH for local development
- **Code Consistency**: Maintain same import structure between local and production environments

#### **6. Documentation & Onboarding**
- **API Documentation**: OpenAPI/Swagger documentation
- **Deployment Guides**: Step-by-step deployment instructions
- **Developer Onboarding**: Setup guides and development environment configuration
- **Troubleshooting Guides**: Common issues and resolution procedures

---

## Technical Architecture Summary

### **Core Technologies:**
- **Backend**: Python 3.13 with AWS Lambda
- **Infrastructure**: AWS CDK with TypeScript and Docker-based bundling
- **Database**: DynamoDB with single-table design
- **Authentication**: AWS Cognito with Apple Identity Provider
- **AI/ML**: AWS Bedrock for translation services
- **Testing**: Pytest with moto for AWS service mocking
- **Code Quality**: Black, flake8, mypy, pre-commit hooks
- **Lambda Layers**: Dual-layer architecture with dependencies and shared code separation

### **Key Design Patterns:**
- **Clean Architecture**: Separation of concerns with service and repository layers
- **Event-Driven**: Lambda functions triggered by API Gateway and Cognito events
- **Single-Table Design**: Efficient DynamoDB access patterns
- **TDD Workflow**: Test-driven development with Red-Green-Refactor
- **Environment-Based**: Separate dev/prod environments with proper resource isolation

### **Security & Compliance:**
- **Authentication**: JWT-based authentication via Cognito
- **Authorization**: API Gateway authorizer with user context injection
- **Data Protection**: Encryption at rest and in transit
- **Secrets Management**: AWS Secrets Manager for sensitive credentials
- **Audit Logging**: Comprehensive logging for security events

### **Performance & Scalability:**
- **Serverless**: Auto-scaling Lambda functions
- **Caching**: DynamoDB DAX for read performance
- **Optimization**: Premium-only translation storage for cost efficiency
- **Monitoring**: CloudWatch metrics and alerting
- **Load Testing**: Performance validation for critical paths

---

## Next Steps & Roadmap

### **Immediate (Next 1-2 weeks):**
1. **Infrastructure Deployment**: Deploy to dev environment
2. **Integration Testing**: End-to-end testing of all APIs
3. **Security Review**: Comprehensive security assessment
4. **Performance Testing**: Load testing and optimization

### **Short Term (Next 1-2 months):**
1. **Production Deployment**: Deploy to production environment
2. **Monitoring Setup**: CloudWatch dashboards and alerting
3. **Documentation**: Complete API documentation and deployment guides
4. **Team Onboarding**: Developer setup and training

### **Long Term (Next 3-6 months):**
1. **Feature Enhancements**: Additional translation models and features
2. **Scale Optimization**: Performance improvements and cost optimization
3. **Security Hardening**: Advanced security features and compliance
4. **Internationalization**: Multi-language support and localization

---

**Current Status**: Ready for infrastructure deployment and production readiness phase. All core functionality implemented with comprehensive test coverage and TDD workflow established.
