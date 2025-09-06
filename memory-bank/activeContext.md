# Active Context - Lingible

## Current Focus: App Store Submission with Google AdMob Integration

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

### ✅ **COMPLETED: Trending System & AI Integration (2024-09-04)**
- **Bedrock AI Integration**: Successfully integrated Claude 3 Haiku for Gen Z slang generation
- **Trending Job Lambda**: Automated daily generation of trending terms at 6 AM UTC
- **Trending API Endpoint**: Tier-based access with free/premium feature differentiation
- **DynamoDB Storage**: Proper GSI indexes for efficient querying by popularity and category
- **IAM Permissions**: Fixed permissions for DynamoDB access and Bedrock AI integration
- **Data Type Handling**: Resolved DynamoDB GSI type mismatches for boolean fields
- **Service Architecture**: Refactored to handle user lookup internally for better separation of concerns
- **Comprehensive Testing**: Successfully tested job execution with 5 terms generated and stored
- **API Documentation**: Updated OpenAPI spec with complete trending endpoint documentation

### ✅ **COMPLETED: Code Quality & Standards (2024-12-19)**
- **Pre-commit Hooks**: Black, flake8, mypy, and trailing whitespace checks
- **Type Safety**: Comprehensive type hints throughout the codebase
- **Code Organization**: Modular handler structure with independent deployment
- **Documentation**: Comprehensive inline documentation and README files

### ✅ **COMPLETED: Dynamic Daily Translation Limits & iOS API Integration (2024-12-19)**
- **Backend API Enhancement**: Added `free_daily_limit` and `premium_daily_limit` fields to UserUsageResponse model
- **Dynamic Configuration**: iOS app now uses backend API values instead of hardcoded limits
- **API Client Regeneration**: Updated iOS Swift client with new fields and proper package structure
- **Build System Fixes**: Resolved Xcode package resolution and build cache problems
- **Project Cleanup**: Consolidated iOS project structure and removed duplicate files
- **Environment Configuration**: Fixed API endpoint to use dev environment (`api.dev.lingible.com`)
- **Type Safety**: Strong typing ensures consistency across all platforms (iOS, Python, TypeScript)
- **OpenAPI Spec Updates**: Updated shared API specification and TypeScript types
- **View Consolidation**: Removed duplicate upgrade views and consolidated into single component

### ✅ **COMPLETED: StoreKit 2 Subscription Integration & TestFlight Setup (2024-12-19)**
- **StoreKit 2 Integration**: Complete SubscriptionManager implementation with real Apple StoreKit products
- **Subscription Purchase Flow**: Full purchase flow with $2.99/month premium subscription pricing
- **Backend Integration**: UserService upgrade API integration with receipt validation
- **Environment Detection**: Automatic development vs production mode switching based on bundle ID
- **Restore Purchases**: Complete restore functionality for existing subscribers
- **TestFlight Ready**: App successfully archived and ready for TestFlight distribution
- **Asset Catalog Fixes**: Resolved all iOS asset warnings (missing AccentColor, AppIcon issues)
- **Code Quality**: Fixed unused variable warnings and unreachable catch blocks
- **Git Repository Cleanup**: Updated .gitignore to exclude iOS build artifacts and user-specific files
- **App Store Connect Setup**: Configured subscription products and TestFlight distribution pipeline

### ✅ **COMPLETED: Translation Quality Improvement (2024-12-19)**
- **Enhanced Prompting**: Improved Bedrock prompts with specific examples and clear rules
- **Natural Language Focus**: Emphasized direct, conversational translations over explanatory responses
- **GenZ Authenticity**: Added authentic examples like "no cap" → "for real" and "it's giving main character energy"
- **Response Parsing**: Enhanced response cleanup to remove formal prefixes and unnecessary punctuation
- **Quality Examples**: Provided specific translation examples for common phrases in both directions
- **Tone Consistency**: Clear rules about maintaining energy level and casual conversational style

### ✅ **COMPLETED: Translation Confidence Improvement (2024-12-19)**
- **Same-Text Prevention**: Added explicit instructions to prevent model from returning identical text
- **Validation Logic**: Implemented `_is_same_text` method to detect when model returns original text
- **Business Event Logging**: Added logging for instances where model returns same text for monitoring
- **Prompt Enhancement**: Added "NEVER return the same text" and "make your best guess" instructions
- **Quality Assurance**: Ensures translations always provide actual value rather than echoing input

### ✅ **COMPLETED: Premium User Status Fix (2024-12-19)**
- **Data Consistency Issue**: Fixed inconsistency where user tier was stored in two separate DynamoDB records
- **Dual Record Update**: Modified `upgrade_user_tier` to update both profile record (SK: "PROFILE") and usage limits record (SK: "USAGE#LIMITS")
- **UI Display Fix**: Resolved issue where "refresh user data" button wasn't updating premium status correctly
- **Repository Pattern**: Ensured both user profile and usage data are consistently updated during tier upgrades
- **User Experience**: Premium users now see correct status immediately after upgrade without manual refresh

### ✅ **COMPLETED: Production Website Deployment (2024-12-19)**
- **Domain Configuration**: Successfully deployed production website to support `lingible.com` and `www.lingible.com`
- **Squarespace DNS Integration**: Configured to work with existing Squarespace domain management (no hosted zone conflicts)
- **SSL Certificate**: Set up email validation for SSL certificates covering both apex and www domains
- **CloudFront Distribution**: Deployed with distribution ID `E1VFIPFKX3U8TB` and domain `didoe7799b8j5.cloudfront.net`
- **S3 Hosting**: Website files deployed to `lingible-website-prod-480421270075-us-east-1` bucket
- **DNS Instructions**: Provided clear Squarespace DNS configuration instructions for A and CNAME records
- **Infrastructure Updates**: Modified website stack to handle production domain without creating conflicting hosted zones

### ✅ **COMPLETED: Translation API & Full System Integration (2024-09-04)**
- **Authentication System**: ✅ Working perfectly with fresh JWT tokens from Cognito
- **Enum Serialization Issues**: ✅ Completely resolved across all repositories
- **Configuration Management**: ✅ Bedrock configuration loading correctly
- **IAM Permissions**: ✅ Added `bedrock:InvokeModel` permission to Lambda function
- **Model Access**: ✅ Updated to accessible Bedrock model
- **SSM Parameter Store**: ✅ Updated with correct model configuration
- **API Gateway Authorization**: ✅ Resolved authorization issues
- **Trending System**: ✅ Fully operational with AI-powered term generation

### 🎯 **CURRENT PRIORITIES:**

#### **1. App Store Submission with Google AdMob Integration**
- **Current Status**: Production archive built, legal docs updated, Apple privacy questionnaire in progress
- **Production Archive**: ✅ Built with correct bundle ID (com.lingible.lingible) and Amplify configuration
- **App Store Connect**: ✅ Setup complete with screenshots, description, keywords, and 1024x1024 icon
- **Legal Documents**: ✅ Updated Privacy Policy and Terms of Service to match Apple privacy questionnaire
- **Apple Privacy Questionnaire**: 🔄 Currently in progress - completed Email Address and User ID sections
- **Google AdMob Decision**: ✅ Decided to integrate AdMob for free tier users only (premium users get ad-free)
- **Production Website**: ✅ Deployed to lingible.com with CloudFront distribution ready for DNS configuration
- **Next Step**: Update legal documents and privacy questionnaire for AdMob integration

#### **2. Environment Configuration & Production Setup**
- **Environment Configuration**: Implement proper environment configuration system for production
- **Build Variants**: Create separate build configurations for dev/staging/production
- **API Endpoint Management**: Dynamic API endpoint configuration based on environment
- **Bundle Identifier Management**: Proper bundle ID management for different environments

#### **3. System Monitoring & Optimization**
- **CloudWatch Dashboards**: Monitor API performance and error rates
- **Cost Optimization**: Monitor and optimize AWS resource usage
- **Performance Tuning**: Optimize Lambda cold starts and DynamoDB queries
- **Security Monitoring**: Monitor for security events and anomalies

#### **4. Production Readiness**
- **Performance Optimization**: Lambda function optimization and cold start reduction
- **Monitoring & Observability**: CloudWatch dashboards and alerting
- **Cost Optimization**: Translation storage optimization and usage tracking
- **Disaster Recovery**: Backup strategies and recovery procedures

#### **5. Testing & Quality Assurance**
- **TDD Enforcement**: Mandatory test-driven development for all changes
- **Test Coverage**: Maintain 90%+ coverage for all new code
- **Integration Testing**: End-to-end testing for critical user flows
- **Performance Testing**: Load testing for API endpoints

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
1. **Production Deployment**: Deploy backend to production environment
2. **TestFlight Testing**: Test complete subscription flow with production APIs
3. **App Store Connect**: Set up subscription products and TestFlight distribution
4. **Environment Configuration**: Update iOS app configuration for production

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

**Current Status**: ✅ **APP STORE SUBMISSION IN PROGRESS** - Production archive built with correct bundle ID and Amplify configuration. Legal documents updated to match Apple privacy questionnaire answers. Production website deployed to lingible.com with CloudFront distribution ready for DNS configuration. Currently working through Apple App Privacy questionnaire and planning Google AdMob integration for free tier users. Ready for final App Store submission once AdMob integration is complete.
