# Authorization Guide

## Overview

This guide explains the comprehensive authorization system for the GenZ Slang Translation App, including API Gateway authorizers, Lambda-based authorization, and tier-based access control.

## Architecture

### 1. API Gateway Authorizer (Lambda Function)
- **File**: `backend/src/handlers/authorizer.py`
- **Purpose**: Validates JWT tokens from Cognito at the API Gateway level
- **Benefits**:
  - Prevents unauthorized requests from reaching Lambda functions
  - Reduces Lambda invocations for invalid tokens
  - Provides user context to Lambda functions

### 2. Lambda-Level Authorization (Simplified)
- **Purpose**: Business logic authorization using authorizer context
- **Benefits**:
  - Uses pre-validated user data from authorizer
  - No additional token validation needed
  - Focus on business logic only

## Authorization Levels

### Public Endpoints
```python
# No API Gateway authorizer configured
def public_handler(event, context):
    # No authentication required
    pass
```

### Protected Endpoints
```python
# API Gateway authorizer validates token
def protected_handler(event, context):
    # User data available from authorizer context
    user_id = event.requestContext.authorizer.user_id
    user_tier = event.requestContext.authorizer.user_tier
    pass
```

### Business Logic Authorization
```python
def premium_feature_handler(event, context):
    # Check user tier from authorizer context
    user_tier = event.requestContext.authorizer.user_tier
    if user_tier not in ["premium", "admin"]:
        return create_forbidden_response("Premium tier required")
    pass
```

## Usage Examples

### Basic Authentication
```python
from src.utils.authorization import require_auth, AuthorizationLevel

@require_auth(level=AuthorizationLevel.AUTHENTICATED)
def my_handler(event, context):
    # Only authenticated users can access
    pass
```

### Tier-Based Access
```python
@require_auth(required_tiers=["premium", "admin"])
def premium_feature_handler(event, context):
    # Only premium and admin users can access
    pass
```

### Attribute-Based Authorization
```python
@require_auth(
    level=AuthorizationLevel.AUTHENTICATED,
    required_attributes={"email_verified": "true"}
)
def verified_user_handler(event, context):
    # Only users with verified email can access
    pass
```

### Combined Authorization
```python
@require_auth(
    level=AuthorizationLevel.PREMIUM,
    required_attributes={"email_verified": "true", "custom:subscription_active": "true"}
)
def premium_verified_handler(event, context):
    # Premium users with verified email and active subscription
    pass
```

## User Tiers

### Free Tier
- Basic translation limits
- Standard features
- Rate limiting

### Premium Tier
- Higher translation limits
- Advanced features
- Priority processing

### Admin Tier
- Full system access
- User management
- System configuration

## API Gateway Configuration

### Authorizer Setup
1. **Create Lambda Authorizer**:
   ```bash
   # Deploy the authorizer function
   aws lambda create-function \
     --function-name genz-translation-authorizer \
     --runtime python3.13 \
     --handler authorizer.lambda_handler \
     --role arn:aws:iam::account:role/lambda-execution-role \
     --zip-file fileb://authorizer.zip
   ```

2. **Configure API Gateway**:
   ```bash
   # Create authorizer in API Gateway
   aws apigateway create-authorizer \
     --rest-api-id your-api-id \
     --name cognito-authorizer \
     --type TOKEN \
     --authorizer-uri arn:aws:apigateway:region:lambda:path/2015-03-31/functions/arn:aws:lambda:region:account:function:genz-translation-authorizer/invocations \
     --authorizer-result-ttl-in-seconds 300
   ```

3. **Apply to Resources**:
   ```bash
   # Apply authorizer to specific methods
   aws apigateway update-method \
     --rest-api-id your-api-id \
     --resource-id your-resource-id \
     --http-method POST \
     --patch-operations op=replace,path=/authorizationType,value=CUSTOM
   ```

## Environment Variables

### Required for Authorizer
```bash
USER_POOL_ID=us-east-1_xxxxxxxxx
USER_POOL_REGION=us-east-1
API_GATEWAY_ARN=arn:aws:execute-api:us-east-1:account:api-id/stage
```

### Required for Lambda Functions
```bash
USER_POOL_ID=us-east-1_xxxxxxxxx
USER_POOL_REGION=us-east-1
```

## Security Best Practices

### 1. Token Validation
- Always validate JWT tokens using Cognito's public keys
- Check token expiration
- Verify issuer and audience claims

### 2. Rate Limiting
- Implement rate limiting per user
- Different limits for different tiers
- Monitor and alert on abuse

### 3. Error Handling
- Don't expose sensitive information in error messages
- Log security events for monitoring
- Use appropriate HTTP status codes

### 4. CORS Configuration
```python
# Example CORS headers
headers = {
    "Access-Control-Allow-Origin": "https://your-app-domain.com",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
    "Access-Control-Allow-Credentials": "true"
}
```

## Monitoring and Logging

### Security Events
- Authentication failures
- Authorization denials
- Token validation errors
- Rate limit violations

### Metrics
- Authentication success/failure rates
- Authorization decision distribution
- Token validation performance
- User tier distribution

### Alerts
- High authentication failure rates
- Unusual authorization patterns
- Token validation errors
- Rate limit violations

## Testing

### Unit Tests
```python
def test_authorization_decorator():
    # Test different authorization levels
    pass

def test_user_tier_validation():
    # Test tier-based access control
    pass

def test_attribute_validation():
    # Test attribute-based authorization
    pass
```

### Integration Tests
```python
def test_api_gateway_authorizer():
    # Test authorizer with valid/invalid tokens
    pass

def test_lambda_authorization():
    # Test decorators with real events
    pass
```

## Troubleshooting

### Common Issues

1. **Token Validation Failures**
   - Check USER_POOL_ID and USER_POOL_REGION
   - Verify JWT token format
   - Check token expiration

2. **Authorization Denials**
   - Verify user tier in Cognito attributes
   - Check required attributes
   - Review authorization level requirements

3. **Performance Issues**
   - Monitor JWKS cache hit rates
   - Check authorizer execution time
   - Optimize token validation

### Debug Mode
```python
# Enable debug logging
import logging
logging.getLogger('src.utils.authorization').setLevel(logging.DEBUG)
```

## Migration Guide

### From Simple Token Validation
1. Replace direct token validation with authorizer decorators
2. Update environment variables
3. Configure API Gateway authorizer
4. Test all endpoints

### From No Authorization
1. Add authentication requirements gradually
2. Start with public endpoints
3. Add authentication to critical endpoints
4. Implement tier-based access control

## Future Enhancements

### Planned Features
- Role-based access control (RBAC)
- Dynamic permission management
- Multi-factor authentication (MFA)
- Session management
- Audit logging

### Integration Opportunities
- AWS IAM integration
- Third-party identity providers
- Single sign-on (SSO)
- Enterprise authentication
