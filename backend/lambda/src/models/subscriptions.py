"""Subscription models for GenZ slang translation app.

🚨 CRITICAL: When modifying these models, ALWAYS update:
1. OpenAPI spec: shared/api/openapi/lingible-api.yaml
2. Regenerate client SDKs (Python, iOS)
"""

from typing import Optional
from datetime import datetime, timezone
from enum import Enum
from pydantic import Field
from .base import LingibleBaseModel


# Domain Models
class StoreEnvironment(str, Enum):
    """Store environment options."""

    SANDBOX = "sandbox"
    PRODUCTION = "production"


class SubscriptionProvider(str, Enum):
    """Subscription providers."""

    APPLE = "apple"
    GOOGLE = "google"


class SubscriptionStatus(str, Enum):
    """Subscription status."""

    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ReceiptValidationStatus(str, Enum):
    """Receipt validation status."""

    VALID = "valid"
    INVALID = "invalid"
    INVALID_TRANSACTION = "invalid_transaction"
    EXPIRED = "expired"
    ALREADY_USED = "already_used"
    ENVIRONMENT_MISMATCH = "environment_mismatch"
    RETRYABLE_ERROR = "retryable_error"


class TransactionData(LingibleBaseModel):
    """Core transaction data model - used throughout the system."""

    provider: SubscriptionProvider = Field(..., description="Subscription provider")
    transaction_id: str = Field(
        ..., min_length=1, description="Provider transaction ID"
    )
    product_id: str = Field(
        ..., min_length=1, description="Product ID from the app store"
    )
    purchase_date: datetime = Field(..., description="Purchase date in ISO format")
    expiration_date: Optional[datetime] = Field(
        None, description="Expiration date in ISO format (for subscriptions)"
    )
    environment: StoreEnvironment = Field(..., description="App Store environment")


class UserSubscription(LingibleBaseModel):
    """User subscription domain model (database storage)."""

    user_id: str = Field(..., description="User ID")
    provider: SubscriptionProvider = Field(..., description="Subscription provider")
    transaction_id: str = Field(..., description="Provider transaction ID")
    status: SubscriptionStatus = Field(
        SubscriptionStatus.ACTIVE, description="Subscription status"
    )
    start_date: datetime = Field(..., description="Subscription start date")
    end_date: Optional[datetime] = Field(None, description="Subscription end date")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Record creation date",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update date",
    )

    def to_api_response(self) -> "UserSubscriptionResponse":
        """Convert to API response model."""
        return UserSubscriptionResponse(
            provider=self.provider,
            transaction_id=self.transaction_id,
            status=self.status,
            start_date=self.start_date,
            end_date=self.end_date,
            created_at=self.created_at,
        )


# API Models
class UserSubscriptionResponse(LingibleBaseModel):
    """API response model for user subscription data."""

    provider: SubscriptionProvider = Field(..., description="Subscription provider")
    transaction_id: str = Field(..., description="Provider transaction ID")
    status: SubscriptionStatus = Field(..., description="Subscription status")
    start_date: datetime = Field(..., description="Subscription start date")
    end_date: Optional[datetime] = Field(None, description="Subscription end date")
    created_at: datetime = Field(..., description="Record creation date")


# Request Models
class UserUpgradeRequest(LingibleBaseModel):
    """Request model for user upgrade endpoint."""

    provider: SubscriptionProvider = Field(
        SubscriptionProvider.APPLE, description="Subscription provider"
    )
    transaction_id: str = Field(
        ..., min_length=1, description="Provider transaction ID"
    )
    product_id: str = Field(
        ..., min_length=1, description="Product ID from the app store"
    )
    purchase_date: datetime = Field(..., description="Purchase date in ISO format")
    expiration_date: Optional[datetime] = Field(
        None, description="Expiration date in ISO format (for subscriptions)"
    )
    environment: StoreEnvironment = Field(..., description="App Store environment")

    def to_transaction_data(self) -> TransactionData:
        """Convert to TransactionData object."""
        return TransactionData(
            provider=self.provider,
            transaction_id=self.transaction_id,
            product_id=self.product_id,
            purchase_date=self.purchase_date,
            expiration_date=self.expiration_date,
            environment=self.environment,
        )


class ReceiptValidationRequest(LingibleBaseModel):
    """Request model for receipt validation - simplified for StoreKit 2."""

    transaction_data: TransactionData = Field(
        ..., description="Transaction data to validate"
    )
    user_id: Optional[str] = Field(None, description="User ID for audit logging")


class ReceiptValidationResult(LingibleBaseModel):
    """Result of receipt validation - simplified for internal use only."""

    is_valid: bool = Field(..., description="Whether receipt is valid")
    status: ReceiptValidationStatus = Field(..., description="Validation status")
    transaction_data: TransactionData = Field(
        ..., description="Validated transaction data"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if validation failed"
    )
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retry")


class AppleNotificationType(str, Enum):
    """Apple notification types."""

    INITIAL_BUY = "INITIAL_BUY"
    RENEWAL = "RENEWAL"
    CANCEL = "CANCEL"
    FAILED_PAYMENT = "FAILED_PAYMENT"
    REFUND = "REFUND"
    REFUND_DECLINED = "REFUND_DECLINED"
    CONSUMPTION_REQUEST = "CONSUMPTION_REQUEST"


class AppleWebhookRequest(LingibleBaseModel):
    """Request model for Apple webhook endpoint - handles JWS payload."""

    # Apple sends the entire payload as a signed JWS
    signed_payload: str = Field(..., description="Signed JWS payload from Apple")


class WebhookResponse(LingibleBaseModel):
    """Response model for webhook endpoints."""

    success: bool = Field(..., description="Whether webhook was processed successfully")
    message: str = Field(..., description="Response message")
