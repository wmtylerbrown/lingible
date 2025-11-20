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
- **Performance**: SnapStart optimization for production

### **Infrastructure:**
- **IaC**: AWS CDK with TypeScript
- **Environment**: Separate dev/prod environments
- **Resource Naming**: `lingible-{service}-{environment}` pattern
- **Deployment**: Automated deployment scripts
- **Lambda Layers**: Unified dependencies layer architecture

### **Database:**
- **Primary**: DynamoDB with multi-table design
- **Tables**:
  - `UsersTable` - User profiles, usage limits, quiz sessions
  - `TranslationsTable` - Translation history
  - `SubmissionsTable` - User slang submissions and moderation
  - `LexiconTable` - Canonical lexicon entries with quiz metadata
  - `TrendingTable` - Trending analytics (90-day TTL)
- **Access Patterns**: Optimized indexes for each table's specific query patterns
- **Documentation**: See `docs/database-schema.md` for complete schema and index definitions

### **Authentication & Security:**
- **Identity Provider**: AWS Cognito
- **External Auth**: Apple Identity Provider
- **API Security**: JWT-based authentication with dual authorizer strategy
- **Authorization**: Custom JWT authorizer + Native Cognito authorizer
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

- **Repository Conventions**:
  - Repositories construct and return strongly typed Pydantic models (no raw `dict` payloads).
  - Shared normalization (Decimal → int/float, singleton → list, enum coercion) lives in `LingibleBaseModel`.
  - Model-level validators handle domain-specific coercion so repositories just pass DynamoDB items through.

### **Handler Organization:**
- **Independent Deployment**: Each handler in its own directory
- **Unified Dependencies**: Single dependencies layer for all handlers
- **Modular Design**: Easy to deploy and maintain individually
- **Performance**: SnapStart optimization for production handlers

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
- **Cold Start Optimization**: SnapStart for production, efficient function design
- **Performance**: Unified dependencies layer reduces package size

### **Database Optimization:**
- **Multi-Table Design**: Dedicated tables for different data domains
- **Partition Key Strategy**: Optimized per-table for specific access patterns
- **GSI Optimization**: Right-sized projections (KEYS_ONLY, INCLUDE) for cost efficiency
- **TTL Management**: Automatic data expiration for trending and temporary data
- **Documentation**: See `docs/database-schema.md` for complete table and index specifications

### **Caching Strategy:**
- **DynamoDB DAX**: Read performance optimization
- **Lambda Layer Caching**: Unified dependencies layer caching
- **API Gateway Caching**: Response caching for static data
- **SnapStart**: Production cold start optimization

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

## 🐍 **Python Environment & Import Management**

### **Virtual Environment Setup:**
```bash
# Create virtual environment at project root
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r backend/lambda/requirements.txt
```

### **Common Python Path Issues & Solutions:**

#### **1. Import Path Problems:**
**Issue**: `ModuleNotFoundError` when running tests or scripts locally
```python
# ❌ This fails in local development
from src.models.user import User

# ✅ Use relative imports in modules
from ..models.user import User

# ✅ Or set PYTHONPATH for scripts
PYTHONPATH=src python -m pytest tests/
```

#### **2. Lambda Layer vs Local Development:**
**Issue**: Different import structures between local and Lambda environments
```python
# Lambda Layer Structure (production)
from models.user import User
from services.user_service import UserService

# Local Development Structure
from src.models.user import User
from src.services.user_service import UserService
```

**Solution**: Use consistent import patterns and PYTHONPATH
```bash
# For local development, always set PYTHONPATH
export PYTHONPATH=backend/lambda/src:$PYTHONPATH

# Or use in commands
PYTHONPATH=backend/lambda/src python -m pytest tests/
```

#### **3. Test Execution Issues:**
**Issue**: Tests fail with import errors when run from different directories
```bash
# ❌ Running from project root without PYTHONPATH
cd /Users/tyler/mobile-app-aws-backend
python -m pytest backend/lambda/tests/

# ✅ Always set PYTHONPATH for tests
cd /Users/tyler/mobile-app-aws-backend/backend/lambda
ENVIRONMENT=test PYTHONPATH=src python -m pytest tests/
```

#### **4. Handler Development Issues:**
**Issue**: Handlers can't find shared modules during local development
```python
# ❌ This fails in local development
from utils.logging import logger

# ✅ Use relative imports in handlers
from ..utils.logging import logger

# ✅ Or ensure PYTHONPATH includes src directory
```

### **Recommended Development Setup:**

#### **1. Environment Variables:**
```bash
# Add to your shell profile (.bashrc, .zshrc, etc.)
export PYTHONPATH="/Users/tyler/mobile-app-aws-backend/backend/lambda/src:$PYTHONPATH"
export ENVIRONMENT="test"
```

#### **2. IDE Configuration:**
```json
// VS Code settings.json
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.terminal.activateEnvironment": true,
    "python.analysis.extraPaths": [
        "./backend/lambda/src"
    ]
}
```

#### **3. Test Execution Scripts:**
```bash
# Create wrapper scripts for consistent execution
#!/bin/bash
# run_tests.sh
cd backend/lambda
ENVIRONMENT=test PYTHONPATH=src python -m pytest tests/ "$@"
```

#### **4. Pre-commit Hook Configuration:**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: bash -c 'cd backend/lambda && ENVIRONMENT=test PYTHONPATH=src python -m pytest tests/'
        language: system
        pass_filenames: false
```

### **Troubleshooting Common Issues:**

#### **1. "ModuleNotFoundError: No module named 'src'"**
```bash
# Solution: Set PYTHONPATH
export PYTHONPATH=backend/lambda/src:$PYTHONPATH
# or
PYTHONPATH=backend/lambda/src python your_script.py
```

#### **2. "ImportError: attempted relative import with no known parent package"**
```python
# Solution: Use absolute imports with PYTHONPATH
# Instead of: from ..models.user import User
# Use: from models.user import User
# And set: PYTHONPATH=backend/lambda/src
```

#### **3. "pydantic_core._pydantic_core" Import Errors**
```bash
# Solution: Ensure virtual environment is activated
source .venv/bin/activate
pip install --upgrade pydantic
# Or rebuild virtual environment
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -r backend/lambda/requirements.txt
```

#### **4. Lambda Layer Import Issues in Production**
```python
# Issue: Lambda can't find modules in layer
# Solution: Ensure layer structure matches import paths
# Layer structure should be:
# python/
#   models/
#   services/
#   repositories/
#   utils/
```

### **Best Practices:**

#### **1. Consistent Import Patterns:**
```python
# ✅ Use absolute imports with PYTHONPATH
from models.user import User
from services.user_service import UserService
from utils.logging import logger

# ❌ Avoid relative imports in production code
from ..models.user import User
from .user_service import UserService
```

#### **2. Environment-Specific Configuration:**
```python
# Always set ENVIRONMENT for local development
ENVIRONMENT=test python -m pytest tests/
ENVIRONMENT=dev python your_script.py
```

#### **3. Virtual Environment Management:**
```bash
# Always use project root .venv
# Never use backend/lambda/venv or other nested environments
python -m venv .venv  # At project root
source .venv/bin/activate
```

#### **4. Test Execution:**
```bash
# Always run tests from backend/lambda directory with PYTHONPATH
cd backend/lambda
ENVIRONMENT=test PYTHONPATH=src python -m pytest tests/
```

### **Development Environment Checklist:**
- [ ] Virtual environment created at project root (`.venv`)
- [ ] Virtual environment activated (`source .venv/bin/activate`)
- [ ] Dependencies installed (`pip install -r backend/lambda/requirements.txt`)
- [ ] PYTHONPATH set to include `backend/lambda/src`
- [ ] ENVIRONMENT variable set for local development
- [ ] IDE configured with correct Python interpreter and paths
- [ ] Tests run from `backend/lambda` directory with proper PYTHONPATH

## 🎯 **Current Technical Status**

### **✅ Completed:**
- **Core Architecture**: Serverless backend with clean architecture
- **API Implementation**: All core APIs implemented and tested
- **Security**: Authentication, authorization, and data protection
- **Testing**: Comprehensive test suite with TDD workflow
- **Infrastructure**: CDK infrastructure with environment separation
- **Monitoring**: CloudWatch integration and alerting
- **Lambda Optimization**: Unified dependencies layer and SnapStart configuration
- **Dual Authorization**: Custom JWT + Native Cognito authorizer implementation

### **🔄 In Progress:**
- **Performance Testing**: SnapStart optimization validation
- **Integration Testing**: End-to-end testing with new architecture

### **📋 Next Steps:**
- **Production Deployment**: Deploy optimized architecture to production
- **Performance Monitoring**: Monitor SnapStart effectiveness
- **Documentation**: Update architecture documentation
- **Team Onboarding**: Developer setup and training

---

**Technical Status**: Lambda architecture optimized with unified dependencies layer and SnapStart configuration. Dual authorization strategy implemented. Ready for production deployment with enhanced performance and simplified architecture.
