"""User models for GenZ slang translation app."""

from typing import Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


# Domain Models
class UserTier(Enum):
    """User subscription tiers."""

    FREE = "free"
    PREMIUM = "premium"


class UserStatus(Enum):
    """User account status."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class User(BaseModel):
    """User domain model."""

    model_config = ConfigDict(from_attributes=True)

    # Core user data (from Cognito)
    user_id: str = Field(..., description="Cognito user ID")
    email: str = Field(..., description="User email")
    username: str = Field(..., description="Cognito username")

    # App-specific data
    tier: UserTier = Field(UserTier.FREE, description="User subscription tier")
    status: UserStatus = Field(UserStatus.ACTIVE, description="User account status")

    # Subscription data
    subscription_start_date: Optional[datetime] = Field(
        None, description="Premium subscription start"
    )
    subscription_end_date: Optional[datetime] = Field(
        None, description="Premium subscription end"
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Account creation date"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update date"
    )


# API Models
class UserUsageResponse(BaseModel):
    """User usage API response - dynamic data, not cacheable."""

    model_config = ConfigDict(from_attributes=True)

    tier: UserTier = Field(..., description="User tier (free/premium)")
    daily_limit: int = Field(..., description="Daily translation limit")
    daily_used: int = Field(..., description="Translations used today")
    daily_remaining: int = Field(..., description="Translations remaining today")
    total_used: int = Field(..., description="Total translations used")
    reset_date: datetime = Field(..., description="Next daily reset date")
