# Lambda Functions & Services

This document describes all Lambda functions and service classes in the Lingible backend.

## API Handlers

API handlers process synchronous HTTP requests from the mobile app via API Gateway.

### Translation

**`translate_api`** - `POST /translate`
- **Purpose**: Translate text between English and GenZ slang
- **Service**: `TranslationService`
- **Repositories**: `LexiconRepository`, `TranslationRepository`
- **Features**:
  - Lexicon matching for known terms
  - Pattern matching for templates
  - LLM fallback via AWS Bedrock
  - History storage (based on user tier)

### User Management

**`user_profile_api`** - `GET /user/profile`, `PUT /user/profile`
- **Purpose**: Get and update user profile
- **Service**: `UserService`
- **Repository**: `UserRepository`

**`user_usage_api`** - `GET /user/usage`
- **Purpose**: Get user usage statistics and limits
- **Service**: `UserService`
- **Repository**: `UserRepository`

**`user_upgrade_api`** - `POST /user/upgrade`
- **Purpose**: Upgrade user tier via Apple subscription
- **Service**: `SubscriptionService`, `UserService`
- **Repositories**: `SubscriptionRepository`, `UserRepository`
- **Features**: Apple StoreKit 2 validation

**`user_account_deletion_api`** - `DELETE /user/account`
- **Purpose**: Delete user account and all associated data
- **Service**: `UserService`
- **Repositories**: All repositories (cascading deletion)

### Translation History

**`get_translation_history_api`** - `GET /translations/history`
- **Purpose**: Get user's translation history with pagination
- **Service**: `TranslationService`
- **Repository**: `TranslationRepository`

**`delete_translation_api`** - `DELETE /translations/{id}`
- **Purpose**: Delete a single translation
- **Service**: `TranslationService`
- **Repository**: `TranslationRepository`

**`delete_translations_api`** - `DELETE /translations/all`
- **Purpose**: Delete all user translations
- **Service**: `TranslationService`
- **Repository**: `TranslationRepository`

### Quiz

**`quiz_history_api`** - `GET /quiz/history`
- **Purpose**: Get user quiz statistics and eligibility
- **Service**: `QuizService`
- **Repositories**: `UserRepository`, `LexiconRepository`

**`quiz_question_api`** - `GET /quiz/question`
- **Purpose**: Get next quiz question (creates/uses session)
- **Service**: `QuizService`
- **Repositories**: `UserRepository`, `LexiconRepository`
- **Features**:
  - Session management (15-minute timeout)
  - Free tier daily limit enforcement
  - Difficulty-based term selection

**`quiz_answer_api`** - `POST /quiz/answer`
- **Purpose**: Submit answer for one question
- **Service**: `QuizService`
- **Repositories**: `UserRepository`, `LexiconRepository`
- **Features**: Time-based scoring, immediate feedback

**`quiz_progress_api`** - `GET /quiz/progress`
- **Purpose**: Get current quiz session progress
- **Service**: `QuizService`
- **Repository**: `UserRepository`

**`quiz_end_api`** - `POST /quiz/end`
- **Purpose**: End quiz session and get final results
- **Service**: `QuizService`
- **Repositories**: `UserRepository`, `LexiconRepository`
- **Features**: Final scoring, statistics update

### Slang Submissions

**`submit_slang_api`** - `POST /slang/submit`
- **Purpose**: Submit a new slang term for moderation
- **Service**: `SlangSubmissionService`
- **Repository**: `SubmissionsRepository`
- **Features**: Input validation, duplicate detection, SNS notification

**`slang_pending_api`** - `GET /slang/pending`
- **Purpose**: Get pending submissions (admin)
- **Service**: `SlangSubmissionService`
- **Repository**: `SubmissionsRepository`

**`slang_admin_approve_api`** - `POST /slang/admin/approve`
- **Purpose**: Approve a submission (admin)
- **Service**: `SlangSubmissionService`
- **Repository**: `SubmissionsRepository`

**`slang_admin_reject_api`** - `POST /slang/admin/reject`
- **Purpose**: Reject a submission (admin)
- **Service**: `SlangSubmissionService`
- **Repository**: `SubmissionsRepository`

**`slang_upvote_api`** - `POST /slang/upvote`
- **Purpose**: Upvote a submission
- **Service**: `SlangSubmissionService`
- **Repository**: `SubmissionsRepository`

### Trending

**`trending_api`** - `GET /trending`
- **Purpose**: Get trending slang terms
- **Service**: `TrendingService`
- **Repository**: `TrendingRepository`
- **Features**: Category filtering, popularity ranking

### Apple Webhooks

**`apple_webhook_api`** - `POST /webhooks/apple/subscription`
- **Purpose**: Handle Apple subscription webhooks (renewals, cancellations)
- **Service**: `SubscriptionService`
- **Repositories**: `SubscriptionRepository`, `UserRepository`
- **Features**: Webhook signature verification, transaction deduplication

### System

**`health_api`** - `GET /health`
- **Purpose**: Health check endpoint
- **No service**: Returns static response

## Async Handlers

Async handlers process background jobs triggered by SNS topics.

### `slang_validation_async`
- **Trigger**: `slangSubmissionsTopic` SNS topic
- **Purpose**: Validate user-submitted slang terms using LLM
- **Service**: `SlangValidationService`
- **Repository**: `SubmissionsRepository`
- **Features**:
  - LLM validation via AWS Bedrock
  - Web search via Tavily API
  - Auto-approval for high-confidence terms
  - Status updates (validated, auto_approved, rejected)

### `export_lexicon_async`
- **Trigger**: Manual invocation or scheduled job
- **Purpose**: Export lexicon data to S3
- **Service**: Export service (direct repository access)
- **Repository**: `LexiconRepository`
- **Features**: S3 export, CSV/JSON formats

### `trending_job_async`
- **Trigger**: Scheduled EventBridge rule
- **Purpose**: Generate trending term lists
- **Service**: `TrendingService`
- **Repositories**: `TrendingRepository`, `UserRepository`
- **Features**:
  - LLM-based trending term generation
  - Popularity score calculation
  - Category-based trending lists

### `user_data_cleanup_async`
- **Trigger**: SNS topic (from pre-deletion trigger)
- **Purpose**: Comprehensive cleanup of user data
- **Service**: Cleanup service (direct repository access)
- **Repositories**: All repositories
- **Features**: Cascading deletion across all tables

## Cognito Triggers

Cognito triggers handle user lifecycle events in Cognito User Pool.

### `cognito_post_confirmation_trigger`
- **Trigger**: Cognito Post Confirmation event
- **Purpose**: Create user in DynamoDB after email confirmation
- **Service**: `UserService`
- **Repository**: `UserRepository`
- **Features**: Idempotent creation, default tier assignment

### `cognito_pre_authentication_trigger`
- **Trigger**: Cognito Pre Authentication event
- **Purpose**: Ensure user exists in DynamoDB before login
- **Service**: `UserService`
- **Repository**: `UserRepository`
- **Features**: Handles Apple Sign-In users who skip email confirmation

### `cognito_pre_user_deletion_trigger`
- **Trigger**: Cognito Pre User Deletion event
- **Purpose**: Mark user as cancelled and queue cleanup
- **Service**: `UserService`
- **Repository**: `UserRepository`
- **Features**: Publishes to cleanup SNS topic

## Service Classes

Service classes contain business logic and orchestrate repository calls.

### `TranslationService`
- **Purpose**: Orchestrate translation workflow
- **Dependencies**: `SlangLexiconService`, `SlangMatchingService`, `SlangLLMService`, `TranslationRepository`
- **Features**: Lexicon matching, pattern matching, LLM fallback, history management

### `UserService`
- **Purpose**: User management and tier operations
- **Dependencies**: `UserRepository`, Cognito client
- **Features**: Profile CRUD, usage tracking, tier upgrades, account deletion

### `QuizService`
- **Purpose**: Quiz generation, scoring, and session management
- **Dependencies**: `UserRepository`, `LexiconRepository`
- **Features**: Question generation, time-based scoring, session management, statistics tracking

### `SlangSubmissionService`
- **Purpose**: Manage user slang term submissions
- **Dependencies**: `SubmissionsRepository`, SNS client
- **Features**: Input validation, duplicate detection, moderation workflow, upvoting

### `SlangValidationService`
- **Purpose**: Validate submissions using LLM and web search
- **Dependencies**: AWS Bedrock, Tavily API client
- **Features**: LLM validation, web search, auto-approval logic, confidence scoring

### `SlangLexiconService`
- **Purpose**: Load and query lexicon data
- **Dependencies**: S3 client, `LexiconRepository`
- **Features**: Lexicon loading from S3, term matching, variant resolution

### `SlangMatchingService`
- **Purpose**: Pattern matching for slang terms
- **Dependencies**: Aho-Corasick automaton
- **Features**: Template matching, overlap resolution, variant fallbacks

### `SlangLLMService`
- **Purpose**: LLM-based translation and generation
- **Dependencies**: AWS Bedrock
- **Features**: English-to-GenZ translation, GenZ-to-English translation, prompt engineering

### `TrendingService`
- **Purpose**: Generate and manage trending terms
- **Dependencies**: `TrendingRepository`, `UserRepository`, AWS Bedrock
- **Features**: Trending generation, popularity scoring, category filtering

### `SubscriptionService`
- **Purpose**: Apple subscription validation and management
- **Dependencies**: `SubscriptionRepository`, `UserRepository`, Apple StoreKit API
- **Features**: StoreKit 2 validation, webhook handling, subscription lifecycle

### `AppleStoreKitService`
- **Purpose**: Apple StoreKit 2 API integration
- **Dependencies**: Apple App Store Server API client
- **Features**: Transaction validation, JWT generation, webhook signature verification

## Data Flow Patterns

### Synchronous API Flow
1. API Gateway receives request
2. Cognito authorizer validates JWT
3. Request routed to API handler
4. Handler calls service layer
5. Service orchestrates repository calls
6. Response returned to client

### Async Processing Flow
1. API handler publishes SNS message
2. SNS triggers async Lambda
3. Async handler calls service layer
4. Service processes job and updates repositories
5. Results logged to CloudWatch

### Cognito Trigger Flow
1. Cognito event occurs (signup, login, deletion)
2. Cognito invokes trigger Lambda
3. Trigger handler calls service layer
4. Service updates `UserRepository`
5. For deletions, publishes cleanup message
