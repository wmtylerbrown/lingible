"""Subscription models for GenZ slang translation app."""

from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


# Enums
class SubscriptionProvider(Enum):
    """Supported subscription providers."""

    APPLE = "apple"
    GOOGLE = "google"
    STRIPE = "stripe"
    PAYPAL = "paypal"


class SubscriptionStatus(Enum):
    """Subscription status."""

    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING = "pending"
    FAILED = "failed"


class SubscriptionAction(Enum):
    """Subscription actions for history tracking."""

    UPGRADE = "upgrade"
    DOWNGRADE = "downgrade"
    CANCEL = "cancel"
    RENEWAL = "renewal"
    FAILED_PAYMENT = "failed_payment"
    RESTORED = "restored"


# Domain Models
class Subscription(BaseModel):
    """Provider-agnostic subscription model for single table design."""

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
        },
        use_enum_values=True,
    )

    # Core fields
    subscription_id: str = Field(..., description="Unique subscription ID")
    user_id: str = Field(..., description="User ID")

    # Provider-agnostic fields
    provider: SubscriptionProvider = Field(..., description="Subscription provider")
    tier: str = Field(..., description="Subscription tier (free/premium)")
    status: SubscriptionStatus = Field(..., description="Subscription status")

    # Provider-specific data (flexible)
    provider_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific data (transaction_id, receipt_data, etc.)",
    )

    # Timestamps
    start_date: datetime = Field(..., description="Subscription start date")
    end_date: Optional[datetime] = Field(None, description="Subscription end date")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Record creation date"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update date"
    )

    def to_api_response(self) -> "SubscriptionResponse":
        """Convert to API response model."""
        return SubscriptionResponse(
            subscription_id=self.subscription_id,
            provider=self.provider.value,
            tier=self.tier,
            status=self.status.value,
            start_date=self.start_date.isoformat(),
            end_date=self.end_date.isoformat() if self.end_date else None,
            created_at=self.created_at.isoformat(),
        )


class SubscriptionHistory(BaseModel):
    """Subscription change history for single table design."""

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
        },
        use_enum_values=True,
    )

    # Core fields
    history_id: str = Field(..., description="Unique history ID")
    user_id: str = Field(..., description="User ID")
    subscription_id: str = Field(..., description="Related subscription ID")

    # Change details
    action: SubscriptionAction = Field(..., description="Action performed")
    old_tier: Optional[str] = Field(None, description="Previous tier")
    new_tier: str = Field(..., description="New tier")
    provider: SubscriptionProvider = Field(..., description="Provider")

    # Provider-specific data for this change
    provider_data: Dict[str, Any] = Field(
        default_factory=dict, description="Provider-specific data for this change"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this change occurred"
    )

    def to_api_response(self) -> "SubscriptionHistoryResponse":
        """Convert to API response model."""
        return SubscriptionHistoryResponse(
            history_id=self.history_id,
            subscription_id=self.subscription_id,
            action=self.action.value,
            old_tier=self.old_tier,
            new_tier=self.new_tier,
            provider=self.provider.value,
            created_at=self.created_at.isoformat(),
        )


# API Models
class SubscriptionResponse(BaseModel):
    """API response model for subscription data."""

    subscription_id: str = Field(..., description="Unique subscription ID")
    provider: str = Field(..., description="Subscription provider")
    tier: str = Field(..., description="Subscription tier")
    status: str = Field(..., description="Subscription status")
    start_date: str = Field(..., description="Subscription start date (ISO format)")
    end_date: Optional[str] = Field(
        None, description="Subscription end date (ISO format)"
    )
    created_at: str = Field(..., description="Record creation date (ISO format)")


class SubscriptionHistoryResponse(BaseModel):
    """API response model for subscription history."""

    history_id: str = Field(..., description="Unique history ID")
    subscription_id: str = Field(..., description="Related subscription ID")
    action: str = Field(..., description="Action performed")
    old_tier: Optional[str] = Field(None, description="Previous tier")
    new_tier: str = Field(..., description="New tier")
    provider: str = Field(..., description="Provider")
    created_at: str = Field(..., description="When this change occurred (ISO format)")


class SubscriptionListResponse(BaseModel):
    """API response model for subscription list."""

    subscriptions: list[SubscriptionResponse] = Field(
        ..., description="List of subscriptions"
    )
    total_count: int = Field(..., ge=0, description="Total number of subscriptions")


class SubscriptionHistoryListResponse(BaseModel):
    """API response model for subscription history list."""

    history: list[SubscriptionHistoryResponse] = Field(
        ..., description="List of history items"
    )
    total_count: int = Field(..., ge=0, description="Total number of history items")


# Request Models
class CreateSubscriptionRequest(BaseModel):
    """Request model for creating a subscription."""

    provider: SubscriptionProvider = Field(..., description="Subscription provider")
    tier: str = Field(..., description="Subscription tier")
    provider_data: Dict[str, Any] = Field(..., description="Provider-specific data")


class UpdateSubscriptionRequest(BaseModel):
    """Request model for updating a subscription."""

    status: Optional[SubscriptionStatus] = Field(
        None, description="New subscription status"
    )
    provider_data: Optional[Dict[str, Any]] = Field(
        None, description="Updated provider data"
    )
    end_date: Optional[datetime] = Field(None, description="New end date")
