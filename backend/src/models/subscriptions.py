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
