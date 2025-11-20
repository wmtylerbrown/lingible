# Lambda Permissions Audit

## Issue Found
The `post-confirmation` Lambda failed with `AccessDeniedException` when trying to create a user in DynamoDB. This indicates missing IAM permissions.

## Analysis Methodology
1. Review each Lambda handler to identify what DynamoDB operations it performs
2. Check what permissions are currently granted in CDK
3. Identify missing permissions
4. Fix all permission issues

## Lambda Functions and Required Permissions

### API Stack Lambdas

#### 1. Post-Confirmation Lambda (Cognito Trigger)
**Handler**: `cognito_post_confirmation_trigger/handler.py`
**Operations**:
- Creates user record in users table (`UserRepository.create_user()` → `put_item`)

**Current Permissions**: ❌ **NONE** - Missing grants!
**Required Permissions**:
- `readWriteTables`: `[usersTable]`

#### 2. Translate Lambda
**Handler**: `translate_api/handler.py`
**Operations**:
- Reads/writes users table (usage tracking, user lookup)
- Reads/writes translations table (save translation)
- Reads lexicon table (for term lookup)

**Current Permissions**: ✅ `readWriteTables: [usersTable, translationsTable], readOnlyTables: [lexiconTable]`
**Status**: ✅ Correct

#### 3. User Profile Lambda
**Handler**: `user_profile_api/handler.py`
**Operations**:
- Reads users table (get user profile)

**Current Permissions**: ✅ `readWriteTables: [usersTable]`
**Status**: ✅ Correct (readWrite includes read)

#### 4. User Usage Lambda
**Handler**: `user_usage_api/handler.py`
**Operations**:
- Reads/writes users table (usage tracking)

**Current Permissions**: ✅ `readWriteTables: [usersTable]`
**Status**: ✅ Correct

#### 5. User Upgrade Lambda
**Handler**: `user_upgrade_api/handler.py`
**Operations**:
- Reads/writes users table (upgrade tier, create subscription)
- Subscriptions are stored in users table (SK: SUBSCRIPTION#ACTIVE)
- Needs SSM parameter for Apple private key

**Current Permissions**: ✅ `readWriteTables: [usersTable], ssmParameters: [applePrivateKeyArn]`
**Status**: ✅ Correct

#### 6. User Account Deletion Lambda
**Handler**: `user_account_deletion_api/handler.py`
**Operations**:
- Reads/writes users table (delete user)
- Reads/writes translations table (delete user translations)
- Needs Cognito permissions (delete user from Cognito)
- Needs SSM parameter for Apple private key

**Current Permissions**: ✅ `readWriteTables: [usersTable, translationsTable], ssmParameters: [appleParameterArn]`
**Additional Permissions**: Needs Cognito permissions (check if granted via additionalStatements)
**Status**: ⚠️ Need to verify Cognito permissions

#### 7. Translation History Lambda
**Handler**: `get_translation_history_api/handler.py`
**Operations**:
- Reads translations table (query user translations)
- Reads users table (user lookup)

**Current Permissions**: ✅ `readOnlyTables: [translationsTable, usersTable]`
**Status**: ✅ Correct

#### 8. Delete Translation Lambda
**Handler**: `delete_translation_api/handler.py`
**Operations**:
- Reads/writes translations table (delete translation)
- Reads users table (user lookup)

**Current Permissions**: ✅ `readWriteTables: [translationsTable], readOnlyTables: [usersTable]`
**Status**: ✅ Correct

#### 9. Delete All Translations Lambda
**Handler**: `delete_translations_api/handler.py`
**Operations**:
- Reads/writes translations table (delete all user translations)
- Reads users table (user lookup)

**Current Permissions**: ✅ `readWriteTables: [translationsTable], readOnlyTables: [usersTable]`
**Status**: ✅ Correct

#### 10. Health Lambda
**Handler**: `health_api/handler.py`
**Operations**:
- No DynamoDB operations (just health check)

**Current Permissions**: ✅ None (correct)
**Status**: ✅ Correct

#### 11. Trending Lambda
**Handler**: `trending_api/handler.py`
**Operations**:
- Reads trending table (get trending terms)
- Reads users table (user lookup for tier checks)

**Current Permissions**: ✅ `readOnlyTables: [trendingTable, usersTable]`
**Status**: ✅ Correct

#### 12. Submit Slang Lambda
**Handler**: `submit_slang_api/handler.py`
**Operations**:
- Reads/writes submissions table (create submission)
- Reads/writes users table (user lookup, usage tracking)
- Publishes to SNS topics (slang submissions, validation requests)
- Needs SSM parameter for Tavily API key

**Current Permissions**: ✅ `readWriteTables: [submissionsTable, usersTable], publishTopics: [slangSubmissionsTopic, slangValidationRequestTopic], ssmParameters: [tavilyApiKeyArn]`
**Status**: ✅ Correct

#### 13. Slang Upvote Lambda
**Handler**: `slang_upvote_api/handler.py`
**Operations**:
- Reads/writes submissions table (update upvotes)
- Reads/writes users table (user lookup, usage tracking)
- Publishes to SNS topics
- Needs SSM parameter for Tavily API key

**Current Permissions**: ✅ `readWriteTables: [submissionsTable, usersTable], publishTopics: [slangSubmissionsTopic, slangValidationRequestTopic], ssmParameters: [tavilyApiKeyArn]`
**Status**: ✅ Correct

#### 14. Slang Pending Lambda
**Handler**: `slang_pending_api/handler.py`
**Operations**:
- Reads submissions table (query pending submissions)
- Needs SSM parameter for Tavily API key

**Current Permissions**: ✅ `readOnlyTables: [submissionsTable], ssmParameters: [tavilyApiKeyArn]`
**Status**: ✅ Correct

#### 15. Slang Admin Approve Lambda
**Handler**: `slang_admin_approve_api/handler.py`
**Operations**:
- Reads/writes submissions table (approve submission, update status)
- Needs SSM parameter for Tavily API key

**Current Permissions**: ✅ `readWriteTables: [submissionsTable], ssmParameters: [tavilyApiKeyArn]`
**Status**: ✅ Correct

#### 16. Slang Admin Reject Lambda
**Handler**: `slang_admin_reject_api/handler.py`
**Operations**:
- Reads/writes submissions table (reject submission, update status)
- Needs SSM parameter for Tavily API key

**Current Permissions**: ✅ `readWriteTables: [submissionsTable], ssmParameters: [tavilyApiKeyArn]`
**Status**: ✅ Correct

#### 17. Quiz Challenge Lambda
**Handler**: `quiz_challenge_api/handler.py`
**Operations**:
- Reads/writes users table (create quiz session, update stats)
- Reads lexicon table (get quiz questions)

**Current Permissions**: ✅ `readWriteTables: [usersTable], readOnlyTables: [lexiconTable]`
**Status**: ✅ Correct

#### 18. Quiz Submit Lambda
**Handler**: `quiz_submit_api/handler.py`
**Operations**:
- Reads/writes users table (update quiz stats, session data)
- Reads/writes lexicon table (update quiz metrics)

**Current Permissions**: ✅ `readWriteTables: [usersTable, lexiconTable]`
**Status**: ✅ Correct

#### 19. Quiz History Lambda
**Handler**: `quiz_history_api/handler.py`
**Operations**:
- Reads/writes users table (query quiz sessions, get stats)
- Reads lexicon table (get term details)

**Current Permissions**: ✅ `readWriteTables: [usersTable], readOnlyTables: [lexiconTable]`
**Status**: ✅ Correct

#### 20. Quiz Progress Lambda
**Handler**: `quiz_progress_api/handler.py`
**Operations**:
- Reads/writes users table (get quiz progress, stats)
- Reads lexicon table (get term details)

**Current Permissions**: ✅ `readWriteTables: [usersTable], readOnlyTables: [lexiconTable]`
**Status**: ✅ Correct

#### 21. Quiz End Lambda
**Handler**: `quiz_end_api/handler.py`
**Operations**:
- Reads/writes users table (finalize quiz session, update stats)
- Reads lexicon table (get term details)

**Current Permissions**: ✅ `readWriteTables: [usersTable], readOnlyTables: [lexiconTable]`
**Status**: ✅ Correct

#### 22. Apple Webhook Lambda
**Handler**: `apple_webhook_api/handler.py`
**Operations**:
- Reads/writes users table (update subscription status)
- Subscriptions stored in users table
- Needs SSM parameter for Apple private key

**Current Permissions**: ✅ `readWriteTables: [usersTable], ssmParameters: [applePrivateKeyArn]`
**Status**: ✅ Correct

### Async Stack Lambdas

#### 23. Slang Validation Processor Lambda
**Handler**: `slang_validation_async/handler.py`
**Operations**:
- Reads/writes submissions table (update validation status)
- Reads/writes users table (user lookup)
- Publishes to SNS topic (slang submissions)
- Needs SSM parameter for Tavily API key

**Current Permissions**: ✅ `readWriteTables: [submissionsTable, usersTable], publishTopics: [slangSubmissionsTopic], ssmParameters: [tavilyParameterArn]`
**Status**: ✅ Correct

#### 24. Export Lexicon Lambda
**Handler**: `export_lexicon_async/handler.py`
**Operations**:
- Reads lexicon table (export all terms)
- Writes to S3 bucket (export file)

**Current Permissions**: ✅ `readOnlyTables: [lexiconTable], writeBuckets: [lexiconBucket]`
**Status**: ✅ Correct

#### 25. User Data Cleanup Lambda
**Handler**: `user_data_cleanup_async/handler.py`
**Operations**:
- Reads/writes users table (delete user data)
- Reads/writes translations table (delete user translations)
- Needs SSM parameter for Apple private key

**Current Permissions**: ✅ `readWriteTables: [usersTable, translationsTable], ssmParameters: [appleParameterArn]`
**Status**: ✅ Correct

#### 26. Trending Job Lambda
**Handler**: `trending_job_async/handler.py`
**Operations**:
- Reads/writes trending table (generate trending terms)
- Reads users table (for analysis)

**Current Permissions**: ✅ `readWriteTables: [trendingTable], readOnlyTables: [usersTable]`
**Status**: ✅ Correct

## Summary of Issues

### Critical Issues (Must Fix)
1. **Post-Confirmation Lambda**: Missing write access to users table
   - **Fix**: Add `grants: { readWriteTables: [this.data.usersTable] }`

### Potential Issues (Need Verification)
1. **User Account Deletion Lambda**: May need explicit Cognito permissions
   - **Check**: Verify if Cognito permissions are granted via `additionalStatements` or environment variables

## Action Items
1. ✅ Fix post-confirmation Lambda permissions
2. ⚠️ Verify user account deletion Lambda has Cognito permissions
3. ✅ Deploy and test permission fixes
4. ✅ Monitor CloudWatch logs for any new permission errors
