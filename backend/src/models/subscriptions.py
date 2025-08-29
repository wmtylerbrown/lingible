"""Subscription models for GenZ slang translation app."""

from typing import Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


# Domain Models
class SubscriptionProvider(Enum):
    """Subscription providers."""

    APPLE = "apple"
    GOOGLE = "google"


class SubscriptionStatus(Enum):
    """Subscription status."""

    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ReceiptValidationStatus(Enum):
    """Receipt validation status."""

    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    ALREADY_USED = "already_used"
    ENVIRONMENT_MISMATCH = "environment_mismatch"
    RETRYABLE_ERROR = "retryable_error"


class UserSubscription(BaseModel):
    """User subscription domain model (database storage)."""

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
        },
        use_enum_values=True,  # Serialize enums as their values
    )

    user_id: str = Field(..., description="User ID")
    provider: SubscriptionProvider = Field(..., description="Subscription provider")
    transaction_id: str = Field(..., description="Provider transaction ID")
    status: SubscriptionStatus = Field(SubscriptionStatus.ACTIVE, description="Subscription status")
    start_date: datetime = Field(..., description="Subscription start date")
    end_date: Optional[datetime] = Field(None, description="Subscription end date")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Record creation date")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update date")

    def to_api_response(self) -> "UserSubscriptionResponse":
        """Convert to API response model."""
        return UserSubscriptionResponse(
            provider=self.provider.value,
            transaction_id=self.transaction_id,
            status=self.status.value,
            start_date=self.start_date.isoformat(),
            end_date=self.end_date.isoformat() if self.end_date else None,
            created_at=self.created_at.isoformat(),
        )


# API Models
class UserSubscriptionResponse(BaseModel):
    """API response model for user subscription data."""

    provider: str = Field(..., description="Subscription provider")
    transaction_id: str = Field(..., description="Provider transaction ID")
    status: str = Field(..., description="Subscription status")
    start_date: str = Field(..., description="Subscription start date (ISO format)")
    end_date: Optional[str] = Field(None, description="Subscription end date (ISO format)")
    created_at: str = Field(..., description="Record creation date (ISO format)")


# Request Models
class UserUpgradeRequest(BaseModel):
    """Request model for user upgrade endpoint."""

    provider: SubscriptionProvider = Field(SubscriptionProvider.APPLE, description="Subscription provider")
    receipt_data: str = Field(..., min_length=1, description="Base64 encoded receipt data")
    transaction_id: str = Field(..., min_length=1, description="Provider transaction ID")


class ReceiptValidationRequest(BaseModel):
    """Request model for receipt validation."""

    provider: SubscriptionProvider = Field(..., description="Receipt provider")
    receipt_data: str = Field(..., min_length=1, description="Receipt data from app store")
    transaction_id: str = Field(..., min_length=1, description="Transaction ID")
    user_id: Optional[str] = Field(None, description="User ID for audit logging")


class ReceiptValidationResult(BaseModel):
    """Result of receipt validation."""

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
        },
        use_enum_values=True,
    )

    is_valid: bool = Field(..., description="Whether receipt is valid")
    status: ReceiptValidationStatus = Field(..., description="Validation status")
    transaction_id: str = Field(..., description="Transaction ID")
    product_id: Optional[str] = Field(None, description="Product ID from receipt")
    purchase_date: Optional[datetime] = Field(None, description="Purchase date")
    expiration_date: Optional[datetime] = Field(None, description="Expiration date")
    environment: Optional[str] = Field(None, description="Environment (sandbox/production)")
    error_message: Optional[str] = Field(None, description="Error message if validation failed")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retry")

    def to_api_response(self) -> "ReceiptValidationResponse":
        """Convert to API response model."""
        return ReceiptValidationResponse(
            is_valid=self.is_valid,
            status=self.status.value,
            transaction_id=self.transaction_id,
            product_id=self.product_id,
            purchase_date=self.purchase_date.isoformat() if self.purchase_date else None,
            expiration_date=self.expiration_date.isoformat() if self.expiration_date else None,
            environment=self.environment,
            error_message=self.error_message,
            retry_after=self.retry_after,
        )


class ReceiptValidationResponse(BaseModel):
    """API response model for receipt validation."""

    is_valid: bool = Field(..., description="Whether receipt is valid")
    status: str = Field(..., description="Validation status")
    transaction_id: str = Field(..., description="Transaction ID")
    product_id: Optional[str] = Field(None, description="Product ID from receipt")
    purchase_date: Optional[str] = Field(None, description="Purchase date (ISO format)")
    expiration_date: Optional[str] = Field(None, description="Expiration date (ISO format)")
    environment: Optional[str] = Field(None, description="Environment (sandbox/production)")
    error_message: Optional[str] = Field(None, description="Error message if validation failed")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retry")


class AppleNotificationType(Enum):
    """Apple notification types."""

    INITIAL_BUY = "INITIAL_BUY"
    RENEWAL = "RENEWAL"
    CANCEL = "CANCEL"
    FAILED_PAYMENT = "FAILED_PAYMENT"
    REFUND = "REFUND"
    REFUND_DECLINED = "REFUND_DECLINED"
    CONSUMPTION_REQUEST = "CONSUMPTION_REQUEST"


class Environment(Enum):
    """Environment types."""

    SANDBOX = "Sandbox"
    PRODUCTION = "Production"


class AppleWebhookRequest(BaseModel):
    """Request model for Apple webhook endpoint."""

    notification_type: AppleNotificationType = Field(..., description="Type of notification")
    transaction_id: str = Field(..., min_length=1, description="Apple transaction ID")
    receipt_data: str = Field(..., min_length=1, description="Base64 encoded receipt data")
    environment: Environment = Field(Environment.PRODUCTION, description="Environment")


class WebhookResponse(BaseModel):
    """Response model for webhook endpoints."""

    success: bool = Field(..., description="Whether webhook was processed successfully")
    message: str = Field(..., description="Response message")
