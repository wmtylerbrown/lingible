# Active Context - Lingible

## Current Focus: Slang Crowdsourcing & System Maintenance (2025-10-11)

### ✅ **COMPLETED: Slang Crowdsourcing with AI Validation (2025-10-11)**
- **AI-Powered Validation**: Complete integration of Tavily web search + AWS Bedrock (Claude) for intelligent slang validation
- **Three-Tier Approval System**:
  1. **Auto-Approval**: High-confidence submissions (≥85%, usage score ≥7) automatically approved
  2. **Community Voting**: Medium-confidence submissions go to community for upvoting
  3. **Rejection**: Low-confidence submissions automatically rejected
- **Admin Oversight**: Manual approve/reject endpoints with SNS notifications on all submissions and approvals
- **User Gamification**: Track `slang_submitted_count` and `slang_approved_count` on user profiles
- **Cost Controls**: CloudWatch alarms, configurable thresholds, web search result limits
- **New API Endpoints**: `/slang/upvote/{id}`, `/slang/pending`, `/slang/admin/approve/{id}`, `/slang/admin/reject/{id}`
- **Infrastructure**: New DynamoDB GSI, Lambda layer for Tavily, IAM permissions for Secrets Manager
- **Immediate Validation**: LLM validation runs synchronously on submission (no queue delays)
- **Complete Testing**: Comprehensive test suite following TDD approach
- **Client SDKs**: Python and Swift SDKs regenerated with new endpoints and user statistics

### ✅ **COMPLETED: Unified Secret Management System (2025-10-11)**
- **Single Script**: Consolidated all secret management into `manage-secrets.js`
- **Removed Unused Secrets**: Eliminated `apple-shared-secret` (legacy StoreKit 1) and `apple-webhook-secret` (never implemented)
- **Active Secrets (3 total)**:
  - `apple-private-key` - Apple Sign-In (Cognito)
  - `apple-iap-private-key` - StoreKit 2 API (receipt validation + webhooks)
  - `tavily-api-key` - Slang validation web search
- **New List Command**: `npm run secrets list <env>` shows all secrets status at a glance
- **Consistent Interface**: Uniform commands for all secret types (create, update, info, delete, list)
- **Documentation**: Comprehensive README updates with new workflow
- **Better UX**: Clear indication of configured vs missing secrets

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

### ✅ **COMPLETED: iOS Environment Configuration & App Store Submission Preparation (2024-12-19)**
- **Environment-Specific Configuration**: Implemented Xcode User-Defined Build Settings for AdMob IDs, API endpoints, and bundle identifiers
- **Automatic Amplify Configuration**: Xcode Build Script automatically switches between dev and production Amplify configurations
- **App Store Submission Ready**: Production archive built with correct bundle ID and legal compliance
- **Privacy Questionnaire**: Completed Apple privacy questionnaire with accurate data usage declarations
- **Project Cleanup**: Removed temporary scripts, outdated documentation, and unnecessary generated files
- **Xcode Package Management**: Fixed package resolution issues and GUID conflicts
- **Build System**: iOS project builds consistently with proper environment-specific configuration
- **Legal Compliance**: Updated Privacy Policy and Terms of Service to match App Store requirements
- **App Store Connect**: Complete setup with screenshots, description, keywords, and subscription products

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

### ✅ **COMPLETED: StoreKit 2 Backend Integration & Apple Configuration Cleanup (2024-12-19)**
- **StoreKit 2 API Migration**: Complete migration from legacy receipt validation to StoreKit 2 transaction validation
- **Apple App Store Server API**: Implemented JWT-based authentication with Apple's official API endpoints
- **Transaction Data Model**: Introduced `TransactionData` model for clean StoreKit 2 transaction handling
- **Receipt Validation Service**: Updated to use Apple's App Store Server API with proper JWT token generation
- **Apple Configuration Cleanup**: Removed unused `shared_secret` from AppleConfig model and config service
- **Environment Variable Integration**: Apple credentials (key_id, team_id, bundle_id) now properly injected via CDK
- **Dependency Management**: Added PyJWT to pyproject.toml receipt-validation group, removed requirements.txt
- **Model Simplification**: Cleaned up redundant models and simplified API request/response structures
- **Production Ready**: Complete StoreKit 2 validation system ready for production deployment

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

### ✅ **COMPLETED: Production API Custom Domain Configuration (2024-12-19)**
- **Custom Domain Setup**: Successfully configured `api.lingible.com` for production API Gateway
- **SSL Certificate**: Issued and validated SSL certificate for `api.lingible.com` (ARN: `arn:aws:acm:us-east-1:480421270075:certificate/8b5bc3dc-608b-472d-896c-4b4407aa3667`)
- **Regional Endpoint**: API Gateway configured with regional endpoint `d-d3a0nvcap4.execute-api.us-east-1.amazonaws.com`
- **Hosted Zone**: Regional hosted zone ID `Z1UJRXOUMOOFQ8` for DNS configuration
- **Backend Stack Updates**: Modified CDK infrastructure to use `api.lingible.com` for production instead of `api.prod.lingible.com`
- **Squarespace DNS Configuration**: CNAME record required: `api` → `d-d3a0nvcap4.execute-api.us-east-1.amazonaws.com`
- **Production App Configuration**: iOS app configured to use `https://api.lingible.com` for production API calls

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

#### **1. Google AdMob Integration & Final App Store Submission**
- **Current Status**: iOS environment configuration complete, App Store submission preparation complete, ready for AdMob integration
- **Production Archive**: ✅ Built with correct bundle ID (com.lingible.lingible) and Amplify configuration
- **App Store Connect**: ✅ Setup complete with screenshots, description, keywords, and 1024x1024 icon
- **Legal Documents**: ✅ Updated Privacy Policy and Terms of Service to match Apple privacy questionnaire
- **Apple Privacy Questionnaire**: ✅ Completed with accurate data usage declarations
- **Environment Configuration**: ✅ Implemented environment-specific configuration system for AdMob, API endpoints, and Amplify
- **Xcode Package Management**: ✅ Fixed package resolution issues and build system
- **Project Cleanup**: ✅ Removed temporary files and organized project structure
- **Next Step**: Complete Google AdMob integration for free tier users and final App Store submission

#### **2. Production Deployment & Monitoring**
- **Production Deployment**: Deploy backend to production environment with proper configuration
- **Monitoring Setup**: CloudWatch dashboards and alerting for production systems
- **Performance Optimization**: Lambda function optimization and cost monitoring
- **Security Monitoring**: Monitor for security events and anomalies

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

### ✅ **COMPLETED: JSON Serialization Fix & Enhanced Logging (2024-12-19)**
- **Root Cause**: Fixed `serialize_model()` method in LingibleBaseModel to recursively handle nested Pydantic models
- **Translation History Fix**: Resolved "Object of type TranslationHistory is not JSON serializable" error
- **Enhanced Logging**: Added comprehensive debug logging with safe serialization for better troubleshooting
- **Development Logging**: Added debug-only logging for development environment with detailed context
- **API Response**: Translation history API now properly serializes nested TranslationHistory objects
- **Deployment**: Successfully deployed fix to development environment

### ✅ **COMPLETED: iOS Recent History Optimization (2024-12-19)**
- **Recent History Limit**: Reduced recent translation history from 20 to 5 items in translation UI
- **Performance Improvement**: Cleaner, more focused recent history display
- **Files Updated**: TranslationView.swift and TranslationViewModel.swift
- **User Experience**: More streamlined translation interface with essential recent items only

### ✅ **COMPLETED: Apple Sign-In Bug Fix & Custom Domain Implementation (2024-12-19)**
- **Dual Implementation Issue**: Fixed conflicting Apple Sign-In implementations (native SignInWithAppleButton vs Amplify WebUI)
- **Single Implementation**: Consolidated to use only Amplify WebUI approach for consistent behavior
- **Custom Domain Setup**: Implemented custom domain `auth.lingible.com` for Cognito OAuth to replace "Trust Cognito" with "Trust Lingible"
- **ACM Certificate**: Created SSL certificate for custom domain with proper validation
- **DNS Configuration**: Set up CNAME records for dev environment (prod requires manual Squarespace configuration)
- **iOS Configuration**: Updated Amplify configuration files to use custom domain
- **User Experience**: Users now see "Trust Lingible" instead of confusing "Trust Cognito" dialog

### ✅ **COMPLETED: iOS Codebase Cleanup & App Store Preparation (2024-12-19)**
- **Swift Compiler Warnings**: Fixed all nil coalescing operator warnings in HistoryView, ProfileView, and TrendingTermCard
- **History UI Sorting**: Fixed translation history to display most recent items first
- **Debug Code Cleanup**: Removed 318+ print statements and wrapped debug-only code in #if DEBUG blocks
- **Mock Services Removal**: Cleaned up mock services from TrendingView and moved to proper test files
- **Empty Catch Blocks**: Fixed all empty catch blocks to include proper error logging
- **Token Logging Removal**: Removed all JWT token and sensitive data logging statements
- **Code Quality**: Ensured all debug-only functions are properly wrapped in #if DEBUG blocks
- **Compilation Errors**: Fixed all syntax errors and missing parameters after cleanup

### ✅ **COMPLETED: Production Archive Creation (2024-12-19)**
- **Production Build**: Successfully created production archive with Release configuration
- **Amplify Configuration**: Verified production amplify_outputs.json is used in archive
- **Code Signing**: Successfully signed with Apple Development certificate
- **Archive Location**: `/Users/tyler/Library/Developer/Xcode/Archives/2025-09-13/Lingible-Production-20250913-183435.xcarchive`
- **Archive Size**: 128MB production-ready build
- **Configuration Verification**: Script confirmed production configuration is properly embedded
- **App Store Ready**: Archive is ready for App Store Connect submission

### ✅ **COMPLETED: Lambda Architecture Simplification & Performance Optimization (2024-12-19)**
- **Unified Dependencies Layer**: Consolidated from 3 separate layers (core, authorizer, receipt-validation) to single `dependenciesLayer`
- **Simplified Build Process**: Removed complex Poetry groups and handler-specific layer assignment logic
- **Direct Requirements.txt**: Dependencies layer now uses `../lambda/requirements.txt` directly instead of generated files
- **SnapStart Configuration**: Added conditional SnapStart support (enabled only in production environment)
- **Alias Management**: Removed SnapStart aliases from dev environment while maintaining them for production
- **Performance Focus**: Optimized for faster cold starts and reduced deployment complexity
- **New /me Endpoint**: Added native Cognito authorizer endpoint for testing authentication flows

### ✅ **COMPLETED: Native Cognito Authorizer Implementation (2024-12-19)**
- **Dual Authorization Strategy**: Implemented both custom JWT authorizer and native Cognito authorizer
- **Native Cognito Endpoint**: Added `/me` endpoint using `apigateway.CognitoUserPoolsAuthorizer`
- **Testing Capability**: Provides alternative authentication method for testing and debugging
- **API Gateway Integration**: Properly configured with `authorizationType: apigateway.AuthorizationType.COGNITO`
- **Lambda Function**: Created `meLambda` function with minimal memory (128MB) and short timeout (10s)
- **Permission Management**: Added proper IAM permissions for API Gateway to invoke the me endpoint

### ✅ **COMPLETED: Apple In-App Purchase API Integration & Bug Fixes (2024-12-19)**
- **In-App Purchase API Setup**: Added separate private key configuration for Apple In-App Purchase API (Key ID: DM2M9NP42M)
- **Secret Management**: Updated manage-apple-secret script to support `iap-private-key` secret type with proper JSON formatting
- **Configuration Updates**: Added `in_app_purchase_key_id` to shared config and updated CDK to pass Apple IAP credentials
- **IAM Permissions**: Updated Lambda functions to access `lingible-apple-iap-private-key-${environment}` secrets
- **Enum Bug Fixes**: Fixed `AttributeError: 'str' object has no attribute 'value'` errors across multiple services
- **String Enum Handling**: Corrected `.value` usage on string enums (StoreEnvironment, SubscriptionProvider, TranslationDirection, LogLevel)
- **Enhanced Logging**: Added detailed JWT token and Apple API request logging for debugging authentication issues
- **Deployment**: Successfully deployed fixes to both dev and prod environments

### ✅ **COMPLETED: Translation Failure UX & Premium Slang Submissions (2025-10-10)**
- **Translation Failure Detection**: Smart detection when Bedrock returns same text (ignoring punctuation)
- **No Charge on Failures**: Users NOT charged when translation fails - credits preserved for actual translations
- **Brand-Voice Messaging**: Randomized failure messages with Gen Z brand voice ("not vibing", "no cap", "Help us out?")
- **Message Variety**: 4-5 variants per failure type for fresh, engaging UX
- **Configurable Messages Module**: `utils/translation_messages.py` - easy to update without touching business logic
- **Configurable Threshold**: `low_confidence_threshold` in LLM config (default 0.3) - tune per environment
- **Premium Slang Submissions**: Complete feature for users to submit slang terms with examples
- **Submission API**: POST `/slang/submit` with rate limiting (10/day), duplicate detection, premium-only
- **Admin Notifications**: SNS topic notifies admins of new submissions for review
- **DynamoDB Table**: `lingible-slang-submissions-{env}` with GSIs for admin queries and user history
- **Submission Context**: Tracks whether submitted from translation failure or manually
- **Infrastructure**: SNS topic, DynamoDB table, Lambda handler all fully wired and tested
- **Test Coverage**: 26 comprehensive tests passing - translation failures, randomization, submissions
- **Client SDKs**: Python & Swift SDKs regenerated with new endpoints and models
- **Fixed Test Infrastructure**: Resolved broken test fixtures that were preventing tests from running

### ✅ **COMPLETED: Slang Translation System - Hybrid LLM Architecture (2025-10-01)**
- **Unified Architecture**: Created clean service-oriented architecture for slang translation
- **Hybrid Approach**: Lexicon-based pattern matching + LLM for intelligent translation
- **Bidirectional Translation**: Both GenZ → English and English → GenZ using same infrastructure
- **Service Structure**:
  - `SlangService` (80 lines) - Main orchestrator for both translation directions
  - `SlangLLMService` (185 lines) - LLM interface with structured JSON prompting
  - `SlangLexiconService` (118 lines) - S3-based lexicon management
  - `SlangMatchingService` (400 lines) - Aho-Corasick pattern matching with age filtering
- **Integrated into TranslationService**: Slang translation fully integrated as drop-in replacement
- **Configuration Consolidation**:
  - Eliminated redundant `BedrockConfig`
  - Created unified `LLMConfig` used by both translation and trending services
  - Single source of truth in `shared/config/backend/{env}.json`
  - Required fields (no defaults) - all values must be explicitly set
- **Strong Typing**:
  - `SlangTranslationResponse` model with `Decimal` confidence scores
  - Eliminated all `Dict[str, Any]` usage
  - Full type safety across entire slang pipeline
- **Code Cleanup**:
  - Removed ~1000+ lines of unused/redundant code
  - Deleted 6+ unused models (TranslationResult, QualityMetrics, etc.)
  - Removed 13 unused config fields
  - Fixed all unused imports and type errors
- **Pre-commit Fixes**: Corrected pre-commit paths to properly check lambda code
- **LLM Prompting**: Structured JSON output with confidence scoring, term mappings, and high-confidence guidelines
- **Confidence Scoring**: LLM returns confidence (0.0-1.0) for translation quality assessment
- **Error Handling**: Proper exception propagation and fallback mechanisms

**Current Status**: ✅ **SLANG TRANSLATION COMPLETE** - Production-ready hybrid slang translation system fully integrated into main translation service. Clean architecture with unified LLM configuration, strong typing throughout, and all code quality checks passing.
