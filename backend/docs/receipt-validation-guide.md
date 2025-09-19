# StoreKit 2 Validation Guide - Lingible

## Overview

This guide covers the implementation of secure StoreKit 2 transaction validation for Apple subscriptions in our Lingible app. StoreKit 2 validation is the modern, secure approach for validating Apple subscriptions and is critical for preventing fraud and ensuring only legitimate payments grant premium access.

## Architecture

### **StoreKit 2 Validation Flow**

```mermaid
graph TD
    A[iOS App Purchase] --> B[StoreKit 2 Transaction]
    B --> C[Send Transaction Data to Backend]
    C --> D[ReceiptValidationService]
    D --> E[Generate JWT Token]
    E --> F[Apple App Store Server API]
    F --> G[Validate Transaction]
    G --> H[Parse Apple Response]
    H --> I[Create/Update Subscription]
```

### **Security Layers**

1. **Apple App Store Server API**: Direct validation with Apple's official API
2. **JWT Authentication**: Secure token-based authentication with Apple
3. **Transaction Deduplication**: Prevent replay attacks
4. **Environment Validation**: Ensure correct sandbox/production
5. **Audit Trail**: Complete logging of all validation attempts

## Apple Store Integration

### **Configuration**

Apple credentials are stored in AWS Secrets Manager and injected via environment variables:

```json
{
  "lingible-apple-private-key-dev": {
    "privateKey": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----",
    "keyId": "ABC123DEF4",
    "teamId": "FJZKRUXQ93",
    "bundleId": "com.lingible.lingible"
  }
}
```

### **StoreKit 2 Transaction Validation**

```python
from services.receipt_validation_service import ReceiptValidationService
from models.subscriptions import ReceiptValidationRequest, TransactionData, StoreEnvironment

# Initialize service
validation_service = ReceiptValidationService()

# Create StoreKit 2 transaction data
transaction_data = TransactionData(
    provider=SubscriptionProvider.APPLE,
    transaction_id="1000000123456789",
    product_id="com.lingible.lingible.premium.monthly",
    purchase_date=datetime.now(timezone.utc),
    expiration_date=datetime.now(timezone.utc) + timedelta(days=30),
    environment=StoreEnvironment.SANDBOX
)

# Create validation request
request = ReceiptValidationRequest(
    transaction_data=transaction_data,
    user_id="user_123"
)

# Validate transaction with Apple's App Store Server API
result = validation_service.validate_storekit2_transaction(request)

if result.is_valid:
    print(f"Valid transaction: {result.transaction_data.transaction_id}")
    print(f"Product: {result.transaction_data.product_id}")
    print(f"Expires: {result.transaction_data.expiration_date}")
else:
    print(f"Invalid transaction: {result.error_message}")
```

### **JWT Token Generation**

The service automatically generates JWT tokens for Apple API authentication:

```python
def _get_apple_jwt_token(self) -> str:
    """Generate JWT token for Apple App Store Server API authentication."""
    header = {
        "alg": "ES256",
        "kid": self.apple_config.key_id,
        "typ": "JWT"
    }

    payload = {
        "iss": self.apple_config.team_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=20),
        "aud": "appstoreconnect-v1",
        "bid": self.apple_config.bundle_id
    }

    return jwt.encode(payload, self.apple_config.private_key, algorithm="ES256", headers=header)
```

### **Apple API Endpoints**

- **Production**: `https://api.storekit.itunes.apple.com/inApps/v1/transactions/{transaction_id}`
- **Sandbox**: `https://api.storekit-sandbox.itunes.apple.com/inApps/v1/transactions/{transaction_id}`

### **Transaction Data Model**

```python
class TransactionData(LingibleBaseModel):
    """Core transaction data model - used throughout the system."""

    provider: SubscriptionProvider = Field(..., description="Subscription provider")
    transaction_id: str = Field(..., min_length=1, description="Provider transaction ID")
    product_id: str = Field(..., min_length=1, description="Product ID from the app store")
    purchase_date: datetime = Field(..., description="Purchase date in ISO format")
    expiration_date: Optional[datetime] = Field(
        None, description="Expiration date in ISO format (for subscriptions)"
    )
    environment: StoreEnvironment = Field(..., description="App Store environment")
```

## Google Play Integration

### **Configuration**

Google Play credentials are stored in AWS Secrets Manager:

```json
{
  "lingible-google-service-account-dev": {
    "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----",
    "client_email": "service-account@project.iam.gserviceaccount.com",
    "project_id": "your-project-id"
  }
}
```

### **Google Play Validation**

```python
# Google Play validation (legacy approach - still supported)
validation_result = self.receipt_validator.validate_receipt(
    provider="google",
    receipt_data=purchase_token,
    transaction_id=order_id,
    user_id=user_id
)
```

## Error Handling

### **Validation Status Codes**

```python
class ReceiptValidationStatus(str, Enum):
    """Receipt validation status codes."""
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    ALREADY_USED = "already_used"
    ENVIRONMENT_MISMATCH = "environment_mismatch"
    RETRYABLE_ERROR = "retryable_error"
    NON_RETRYABLE_ERROR = "non_retryable_error"
```

### **Error Response Structure**

```python
class ReceiptValidationResult(LingibleBaseModel):
    """Result of receipt validation."""

    is_valid: bool = Field(..., description="Whether the receipt is valid")
    status: ReceiptValidationStatus = Field(..., description="Validation status")
    transaction_data: Optional[TransactionData] = Field(None, description="Validated transaction data")
    error_message: Optional[str] = Field(None, description="Error message if validation failed")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retry")
```

## Testing

### **Unit Tests**

```python
def test_storekit2_validation():
    """Test StoreKit 2 transaction validation."""
    # Mock Apple API response
    mock_response = {
        "signedTransactionInfo": "base64_encoded_transaction_info"
    }

    # Test validation
    result = validation_service.validate_storekit2_transaction(request)

    assert result.is_valid == True
    assert result.transaction_data.transaction_id == "1000000123456789"
```

### **Integration Tests**

```python
def test_end_to_end_subscription():
    """Test complete subscription flow."""
    # 1. Create subscription request
    # 2. Validate with Apple
    # 3. Create subscription record
    # 4. Update user tier
    pass
```

## Security Best Practices

1. **Never store private keys in code**: Use AWS Secrets Manager
2. **Validate environment**: Ensure sandbox/production consistency
3. **Implement retry logic**: Handle temporary Apple API failures
4. **Log all attempts**: Maintain audit trail for security
5. **Rate limiting**: Prevent abuse of validation endpoints
6. **Transaction deduplication**: Prevent replay attacks

## Monitoring

### **CloudWatch Metrics**

- `ReceiptValidationSuccess`: Successful validations
- `ReceiptValidationFailure`: Failed validations
- `ReceiptValidationLatency`: Validation response time
- `AppleAPIErrors`: Apple API error rates

### **Alerts**

- High validation failure rate (>5%)
- Apple API timeout rate (>1%)
- JWT token generation failures
- Unusual validation patterns

## Troubleshooting

### **Common Issues**

1. **JWT Token Invalid**: Check private key format and key ID
2. **Transaction Not Found**: Verify transaction ID and environment
3. **Environment Mismatch**: Ensure sandbox/production consistency
4. **Rate Limiting**: Implement exponential backoff

### **Debug Logging**

Enable debug logging to troubleshoot validation issues:

```python
logger.log_business_event(
    "storekit2_transaction_validation_started",
    {
        "provider": request.transaction_data.provider,
        "transaction_id": request.transaction_data.transaction_id,
        "user_id": request.user_id,
    },
)
```

## Migration from Legacy Receipt Validation

### **Key Changes**

1. **No more receipt data**: Use transaction data directly
2. **JWT authentication**: Replace shared secret with JWT tokens
3. **Apple App Store Server API**: Use modern API endpoints
4. **Transaction model**: Use `TransactionData` instead of receipt strings

### **Backward Compatibility**

The system maintains backward compatibility with legacy receipt validation for Google Play while using StoreKit 2 for Apple subscriptions.

## Production Deployment

### **Prerequisites**

1. Apple Developer account with App Store Connect access
2. Private key (.p8 file) from App Store Connect
3. Key ID and Team ID from Apple Developer account
4. AWS Secrets Manager configured with Apple credentials

### **Deployment Steps**

1. Store Apple credentials in AWS Secrets Manager
2. Deploy backend with StoreKit 2 validation
3. Update iOS app to use StoreKit 2 transaction data
4. Test with sandbox environment
5. Deploy to production

## Support

For issues with StoreKit 2 validation:

1. Check CloudWatch logs for detailed error messages
2. Verify Apple credentials in AWS Secrets Manager
3. Test with sandbox environment first
4. Review Apple's App Store Server API documentation
5. Contact Apple Developer Support for API issues
