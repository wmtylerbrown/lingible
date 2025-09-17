# Authorization Guide

## Overview

This guide explains the comprehensive authorization system for the Lingible Translation App, using AWS API Gateway's native Cognito authorizer for secure, scalable authentication.

## Architecture

### 1. Native Cognito Authorizer
- **Type**: API Gateway Cognito User Pools Authorizer
- **Purpose**: Validates JWT tokens from Cognito at the API Gateway level
- **Benefits**:
  - Prevents unauthorized requests from reaching Lambda functions
  - Reduces Lambda invocations for invalid tokens
  - Provides user context to Lambda functions
  - No custom Lambda function needed for authorization
  - Lower cost and complexity

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
# API Gateway Cognito authorizer validates token
def protected_handler(event, context):
    # User data available from authorizer context
    user_id = event.requestContext.authorizer.claims.sub
    email = event.requestContext.authorizer.claims.email
    user_tier = event.requestContext.authorizer.claims.get('custom:user_tier', 'free')
    pass
```

### Business Logic Authorization
```python
def premium_feature_handler(event, context):
    # Check user tier from authorizer context
    user_tier = event.requestContext.authorizer.claims.get('custom:user_tier', 'free')
    if user_tier not in ["premium", "admin"]:
        return create_forbidden_response("Premium tier required")
    pass
```

## Token Types

### ID Token (Primary)
- **Used for**: API Gateway authentication
- **Contains**: User identity claims (sub, email, etc.)
- **Validation**: Handled by native Cognito authorizer

### Access Token
- **Used for**: AWS service calls (if needed)
- **Contains**: AWS service permissions
- **Validation**: Not used for API Gateway authentication

## Multi-Provider Support

### Cognito User Pool Users
- **Authentication**: Direct Cognito authentication
- **Claims**: Full Cognito claims including `event_id`, `origin_jti`, etc.
- **Token**: ID token with standard Cognito structure

### Apple Sign-In Users
- **Authentication**: Apple OAuth → Cognito
- **Claims**: Apple-specific claims including `at_hash`
- **Token**: ID token with Apple-specific structure
- **Missing Claims**: Some Cognito-specific fields (handled gracefully)

## Implementation

### 1. API Gateway Configuration
```typescript
// CDK Configuration
const cognitoAuthorizer = new apigateway.CognitoUserPoolsAuthorizer(this, 'NativeCognitoAuthorizer', {
  cognitoUserPools: [this.userPool],
  authorizerName: 'NativeCognitoAuthorizer',
  identitySource: 'method.request.header.Authorization',
});
```

### 2. Lambda Function Integration
```typescript
// Apply to API methods
translate.addMethod('POST', new apigateway.LambdaIntegration(this.translateLambda), {
  authorizer: cognitoAuthorizer,
  authorizationType: apigateway.AuthorizationType.COGNITO,
  methodResponses: [
    {
      statusCode: '200',
      responseModels: {
        'application/json': successModel,
      },
    },
    {
      statusCode: '401',
      responseModels: {
        'application/json': errorModel,
      },
    },
  ],
});
```

### 3. Client Authentication
```python
# Python Client SDK
def get_auth_headers(self) -> Dict[str, str]:
    token = self.get_valid_token()  # Returns ID token
    return {
        'Authorization': f'Bearer {token}'
    }
```

```swift
// iOS App
func getAuthToken() async throws -> String {
    // Extract ID token from Cognito session
    return id_token  // Not access_token
}
```

## Claims Structure

### Standard JWT Claims (Always Present)
- `sub`: Subject - unique user identifier
- `aud`: Audience - client ID
- `iss`: Issuer - Cognito User Pool URL
- `exp`: Expiration time (Unix timestamp)
- `iat`: Issued at time (Unix timestamp)
- `jti`: JWT ID - unique token identifier
- `email`: User email address

### Cognito-Specific Claims (Optional)
- `token_use`: Token use type (id, access, refresh)
- `auth_time`: Authentication time (Unix timestamp)
- `cognito:username`: Cognito username
- `event_id`: Event ID for this authentication
- `origin_jti`: Original JWT ID

### Apple-Specific Claims (Optional)
- `at_hash`: Apple OAuth access token hash

### Custom Claims (Optional)
- `custom:user_tier`: User tier (free, premium)
- `custom:role`: User role
- `email_verified`: Email verification status
- `phone_number`: User phone number

## Error Handling

### 401 Unauthorized
- **Cause**: Invalid or expired token
- **Response**: Clear error message
- **Action**: Client should refresh token or re-authenticate

### 403 Forbidden
- **Cause**: Valid token but insufficient permissions
- **Response**: Specific permission error
- **Action**: Client should check user tier/role

## Security Considerations

### Token Validation
- **Automatic**: Handled by API Gateway
- **No Custom Code**: No need for manual JWT validation
- **Performance**: Optimized by AWS infrastructure

### User Context
- **Injection**: Automatic user context injection
- **Validation**: Pre-validated by API Gateway
- **Security**: No risk of token manipulation

### Multi-Provider Support
- **Flexible**: Handles both Cognito and Apple users
- **Graceful**: Missing claims handled gracefully
- **Consistent**: Same API for all authentication types

## Migration from Custom Authorizer

### Benefits of Native Authorizer
- **Cost Reduction**: No custom Lambda function needed
- **Simplified Architecture**: Fewer moving parts
- **Better Performance**: AWS-optimized validation
- **Easier Maintenance**: No custom authorization code

### Migration Steps
1. **Update CDK**: Replace custom authorizer with native Cognito authorizer
2. **Update Models**: Make Cognito-specific claims optional
3. **Update Clients**: Use ID token instead of Access token
4. **Test**: Verify both Cognito and Apple users work
5. **Deploy**: Remove custom authorizer Lambda function

## Troubleshooting

### Common Issues
1. **401 Errors**: Check token type (ID vs Access)
2. **Missing Claims**: Verify user authentication method
3. **Validation Errors**: Check Pydantic model flexibility

### Debugging
1. **CloudWatch Logs**: Check Lambda function logs
2. **API Gateway Logs**: Check authorizer logs
3. **Token Inspection**: Decode JWT to verify claims

## Best Practices

### Token Management
- **Use ID Token**: For API Gateway authentication
- **Handle Refresh**: Implement token refresh logic
- **Error Handling**: Graceful handling of expired tokens

### User Context
- **Extract Claims**: Use `event.requestContext.authorizer.claims`
- **Handle Missing Fields**: Use optional fields gracefully
- **Validate Business Logic**: Check user tier/role as needed

### Security
- **Least Privilege**: Only request necessary claims
- **Token Storage**: Secure token storage in clients
- **Error Messages**: Don't expose sensitive information

---

**Last Updated**: December 2024
**Version**: 2.0 (Native Cognito Authorizer)
