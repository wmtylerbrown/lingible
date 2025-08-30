# Cognito Triggers Setup

This document explains how to set up AWS Cognito triggers to automatically create users in our DynamoDB table when they sign up through Cognito.

## Overview

We use three Cognito triggers to manage user lifecycle in our DynamoDB user table:

1. **Post Confirmation Trigger** - Creates user after email confirmation
2. **Pre Authentication Trigger** - Ensures user exists before login (handles Sign in with Apple)
3. **Pre User Deletion Trigger** - Cleans up user data before Cognito deletion

## Lambda Functions

### 1. Post Confirmation Handler
- **Function:** `post_confirmation_handler`
- **Trigger:** Cognito Post Confirmation
- **Purpose:** Creates user in DynamoDB after email confirmation
- **File:** `src/handlers/cognito_post_confirmation.py`

### 2. Pre Authentication Handler
- **Function:** `pre_authentication_handler`
- **Trigger:** Cognito Pre Authentication
- **Purpose:** Ensures user exists in DynamoDB before login
- **File:** `src/handlers/cognito_pre_authentication.py`

### 3. Pre User Deletion Handler
- **Function:** `pre_user_deletion_handler`
- **Trigger:** Cognito Pre User Deletion
- **Purpose:** Marks user as cancelled and queues cleanup job
- **File:** `src/handlers/cognito_pre_user_deletion.py`

### 4. User Data Cleanup Handler
- **Function:** `cleanup_user_data_handler`
- **Trigger:** Background job (SQS/Step Functions)
- **Purpose:** Comprehensive cleanup of user data from all tables
- **File:** `src/handlers/user_data_cleanup.py`

## Setup Instructions

### 1. Deploy Lambda Functions

Deploy the trigger handlers as separate Lambda functions:

```bash
# Deploy post confirmation handler
aws lambda create-function \
  --function-name lingible-post-confirmation \
  --runtime python3.11 \
  --handler src.handlers.cognito_post_confirmation.post_confirmation_handler \
  --role arn:aws:iam::ACCOUNT:role/lambda-execution-role \
  --zip-file fileb://function.zip

# Deploy pre authentication handler
aws lambda create-function \
  --function-name lingible-pre-authentication \
  --runtime python3.11 \
  --handler src.handlers.cognito_pre_authentication.pre_authentication_handler \
  --role arn:aws:iam::ACCOUNT:role/lambda-execution-role \
  --zip-file fileb://function.zip
```

### 2. Configure Cognito User Pool

Add the triggers to your Cognito User Pool:

```bash
aws cognito-idp update-user-pool \
  --user-pool-id YOUR_USER_POOL_ID \
  --lambda-config \
    PostConfirmation=arn:aws:lambda:REGION:ACCOUNT:function:lingible-post-confirmation,\
PreAuthentication=arn:aws:lambda:REGION:ACCOUNT:function:lingible-pre-authentication
```

### 3. Grant Cognito Permissions

Add permission for Cognito to invoke the Lambda functions:

```bash
# Post confirmation
aws lambda add-permission \
    --function-name lingible-post-confirmation \
  --statement-id cognito-post-confirmation \
  --action lambda:InvokeFunction \
  --principal cognito-idp.amazonaws.com \
  --source-arn arn:aws:cognito-idp:REGION:ACCOUNT:userpool/YOUR_USER_POOL_ID

# Pre authentication
aws lambda add-permission \
    --function-name lingible-pre-authentication \
  --statement-id cognito-pre-authentication \
  --action lambda:InvokeFunction \
  --principal cognito-idp.amazonaws.com \
  --source-arn arn:aws:cognito-idp:REGION:ACCOUNT:userpool/YOUR_USER_POOL_ID
```

## User Flow

### Direct Sign Up
1. User signs up in app → Cognito
2. User confirms email → Cognito
3. **Post Confirmation Trigger** → Creates DynamoDB user
4. User can use app

### Sign in with Apple
1. User taps "Sign in with Apple" → Cognito
2. Apple authenticates user → Cognito
3. **Pre Authentication Trigger** → Creates DynamoDB user (if missing)
4. User can use app

### Regular Login
1. User logs in → Cognito
2. **Pre Authentication Trigger** → Ensures DynamoDB user exists
3. User can use app

## Error Handling

- **Non-blocking:** Triggers don't fail the Cognito flow
- **Logging:** All operations are logged for debugging
- **Idempotent:** Safe to run multiple times (checks if user exists)

## Monitoring

Monitor the triggers through:
- CloudWatch Logs
- X-Ray tracing
- Business event logs in our logging system

## Testing

Test the triggers by:
1. Creating a test user in Cognito
2. Checking DynamoDB for the user record
3. Verifying logs show successful creation
