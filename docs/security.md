# Security Practices

## Overview

This document outlines security practices for the Lingible backend, including secrets management, authentication, authorization, and data protection.

## Secrets Management

### SSM Parameter Store (Preferred)

**SecureString Parameters**:
- `/lingible/{env}/secrets/apple-iap-private-key` - Apple IAP private key
- `/lingible/{env}/secrets/tavily-api-key` - Tavily web search API key

**Benefits**:
- Encrypted at rest (SecureString)
- Lower cost than Secrets Manager
- Values never appear in CloudFormation templates
- Managed via `backend/cdk/scripts/manage-secrets.js`

**IAM Permissions**:
- Lambda functions explicitly request access via `ssm:GetParameter`
- Least-privilege: only functions that need a secret get access
- No wildcard policies

### Secrets Manager (Cognito Only)

**Secrets**:
- `lingible-apple-private-key-{env}` - Cognito Apple Sign-In credentials

**Why Secrets Manager**:
- Required by CDK for Cognito identity provider configuration
- CDK `SecretValue.secretsManager()` integration

**Management**:
- Created/updated via `backend/cdk/scripts/manage-secrets.js`
- Never embedded in CloudFormation templates

### Secret Creation Script

```bash
cd backend/cdk
npm run secrets create apple-iap-private-key dev
npm run secrets update tavily-api-key prod
npm run secrets list dev
```

The script ensures values are provided interactively and never logged or stored in version control.

## Authentication

### API Gateway Cognito Authorizer

**Native Authorizer**:
- Validates JWT tokens at API Gateway level
- Prevents unauthorized requests from reaching Lambda
- Reduces Lambda invocations for invalid tokens
- No custom Lambda function needed

**Token Validation**:
- Automatic signature verification using Cognito public keys
- Expiration checking
- Issuer validation
- No custom validation code required

### JWT Token Structure

**Standard Claims**:
- `sub`: User ID (unique identifier)
- `email`: User email address
- `aud`, `iss`, `exp`, `iat`: Standard JWT claims

**Custom Claims**:
- `custom:user_tier`: User tier (free, premium)

**Token Type**:
- Use **ID token** (not access token) for API Gateway authentication
- ID token contains user identity claims
- Access token is for AWS service calls (not used here)

## Authorization

### API Gateway Level

**Public Endpoints**:
- No authorizer configured
- Example: `/health`

**Protected Endpoints**:
- Cognito authorizer required
- User context available in Lambda via `event.requestContext.authorizer.claims`

### Lambda Level

**Business Logic Authorization**:
- Tier checks (free vs premium features)
- Resource ownership validation
- Admin-only operations

**Implementation**:
```python
from utils.handler_authorization import HandlerAuthorization

@HandlerAuthorization.require_user
def handler(event, context):
    user_id = event.requestContext.authorizer.claims['sub']
    user_tier = event.requestContext.authorizer.claims.get('custom:user_tier', 'free')

    if user_tier != 'premium' and requires_premium:
        return create_forbidden_response("Premium tier required")
```

## Data Protection

### DynamoDB Encryption

**At Rest**:
- Server-side encryption (SSE) enabled on all tables
- AWS-managed encryption keys

**In Transit**:
- All API calls use HTTPS/TLS
- DynamoDB API calls encrypted by default

### Point-in-Time Recovery

**Enabled Tables**:
- `UsersTable`
- `TranslationsTable`
- `SubmissionsTable`
- `LexiconTable`
- `TrendingTable` (optional, can be disabled to save cost)

**Recovery Window**: 35 days

### TTL (Time-To-Live)

**TTL-Enabled Data**:
- Trending analytics (90 days)
- Quiz sessions (15-minute timeout)
- Temporary user data

**Benefits**:
- Automatic cleanup of sensitive/transient data
- Cost reduction (fewer items to scan)
- Compliance (data retention limits)

### Data Access Patterns

**Least Privilege IAM**:
- Each Lambda function only gets access to tables it needs
- Granular SSM parameter access
- No wildcard policies

**Repository Pattern**:
- All data access goes through repository classes
- Centralized validation and sanitization
- Type-safe models prevent injection attacks

## Apple Credentials Security

### Private Key Storage

**Apple IAP Key**:
- Stored in SSM Parameter Store as SecureString
- Path: `/lingible/{env}/secrets/apple-iap-private-key`
- Retrieved at runtime by `ConfigService`
- Never logged or exposed in CloudFormation

**Cognito Apple Key**:
- Stored in Secrets Manager
- Required by CDK for identity provider configuration
- Managed via `manage-secrets.js` script

### Key Format Validation

**Pydantic Validation**:
```python
@field_validator('private_key', mode='before')
@classmethod
def validate_private_key(cls, v: Any) -> bytes:
    if isinstance(v, str):
        v = v.encode('utf-8')
    if not v.startswith(b'-----BEGIN PRIVATE KEY-----'):
        raise ValueError('Invalid private key format')
    return v
```

### JWT Generation

**Apple API Authentication**:
- ES256 algorithm (ECDSA P-256)
- Key ID from SSM parameter
- Team ID from SSM parameter
- 20-minute expiration

## Webhook Security

### Apple Subscription Webhooks

**Signature Verification**:
- Verify webhook signature using Apple's public key
- Prevents replay attacks
- Ensures webhook authenticity

**Transaction Deduplication**:
- Check for existing transactions before processing
- Prevents duplicate subscription creation
- Idempotent webhook handling

### Environment Validation

**Sandbox vs Production**:
- Validate transaction environment matches deployment
- Prevent sandbox transactions in production
- Separate credentials per environment

## Logging & Monitoring

### Sensitive Data

**Never Log**:
- Private keys
- API keys
- JWT tokens (full tokens)
- User passwords
- Payment information

**Safe to Log**:
- User IDs (not PII)
- Operation names
- Error messages (sanitized)
- Performance metrics

### CloudWatch Logs

**Retention**:
- 7 days for most functions
- 30 days for critical functions (authorization, payments)

**Encryption**:
- Logs encrypted at rest
- KMS encryption available for sensitive logs

## Best Practices

### Code Security

1. **Type Safety**: Use Pydantic models for all inputs/outputs
2. **Input Validation**: Validate and sanitize all user inputs
3. **Error Handling**: Don't expose internal errors to clients
4. **Dependency Updates**: Keep dependencies up to date

### Infrastructure Security

1. **Least Privilege**: Grant minimum required permissions
2. **Environment Isolation**: Separate dev/prod credentials
3. **Secret Rotation**: Rotate secrets periodically
4. **Audit Logging**: Log all security-relevant events

### Deployment Security

1. **No Secrets in Code**: All secrets in SSM/Secrets Manager
2. **No Secrets in CloudFormation**: Use parameter references
3. **Secure Scripts**: Interactive secret input only
4. **Access Control**: Limit who can deploy to production
