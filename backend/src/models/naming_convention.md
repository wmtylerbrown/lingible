# Model Naming Convention

## Overview
Clear, consistent naming for different types of models based on their purpose and usage.

## Model Categories

### 1. Domain Models (Core Business Entities)
**Purpose**: Primary business entities, used for DB storage and internal operations
**Naming**: Simple, descriptive names without suffixes
**Examples**:
- `User` - User profile and account data
- `Translation` - Translation record (was TranslationResponse)
- `TranslationHistory` - Translation history record (was TranslationHistoryItem)
- `UsageLimit` - User usage tracking data

### 2. API Request Models
**Purpose**: Models for incoming API requests
**Naming**: `{Entity}Request` or `{Action}Request`
**Examples**:
- `TranslationRequest` - Translation API request (was TranslationRequestBody)
- `UserProfileRequest` - User profile update request
- `UserUpgradeRequest` - User tier upgrade request

### 3. API Response Models (Derived/Computed Data)
**Purpose**: Models for API responses that contain derived or computed data
**Naming**: `{Entity}Response` or `{Action}Response`
**Examples**:
- `UserUsageResponse` - User usage statistics (derived from UsageLimit + config)
- `TranslationHistoryResponse` - Paginated translation history (collection)
- `UsageLimitResponse` - Usage limits with derived fields (daily_remaining, etc.)

### 4. External API Models
**Purpose**: Models for external service integrations
**Naming**: `{Service}{Action}` or `{Service}{Entity}`
**Examples**:
- `BedrockRequest` - AWS Bedrock API request
- `BedrockResponse` - AWS Bedrock API response
- `CognitoUser` - AWS Cognito user data

### 5. Event Models
**Purpose**: Models for Lambda event parsing
**Naming**: `{EventType}Event`
**Examples**:
- `TranslationEvent` - Translation Lambda event
- `UserProfileEvent` - User profile Lambda event

## Migration Plan

### Phase 1: Rename Translation Models
- `TranslationResponse` → `Translation` (domain model)
- `TranslationHistoryItem` → `TranslationHistory` (domain model)
- `TranslationRequestBody` → `TranslationRequest` (API request)
- Keep `TranslationHistoryResponse` (API response collection)

### Phase 2: Organize by Purpose
- Group models by their primary purpose
- Add clear comments indicating usage
- Ensure consistent serialization config

### Phase 3: Update References
- Update all imports and references
- Update handler and service code
- Update documentation

## Benefits
1. **Clear Purpose**: Model name immediately indicates its role
2. **Consistent Patterns**: Predictable naming across the codebase
3. **Better Organization**: Logical grouping by purpose
4. **Easier Maintenance**: Clear boundaries between different model types
5. **Reduced Confusion**: No more guessing what a model is for
