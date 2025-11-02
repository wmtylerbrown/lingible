"""User models for GenZ slang translation app."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import Field
from .base import LingibleBaseModel


# Domain Models
class UserTier(str, Enum):
    """User subscription tiers."""

    FREE = "free"
    PREMIUM = "premium"


class UserStatus(str, Enum):
    """User account status."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class User(LingibleBaseModel):
    """User domain model."""

    # Core user data (from Cognito)
    user_id: str = Field(..., description="Cognito user ID")
    email: str = Field(..., description="User email")
    username: str = Field(..., description="Cognito username")

    # App-specific data
    tier: UserTier = Field(UserTier.FREE, description="User subscription tier")
    status: UserStatus = Field(UserStatus.ACTIVE, description="User account status")

    # Slang contribution statistics
    slang_submitted_count: int = Field(
        default=0, ge=0, description="Total slang terms submitted by user"
    )
    slang_approved_count: int = Field(
        default=0, ge=0, description="Total slang terms approved (auto or manual)"
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Account creation date",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update date",
    )

    def to_api_response(self) -> "UserResponse":
        """Convert to API response model."""
        return UserResponse(
            user_id=self.user_id,
            email=self.email,
            username=self.username,
            tier=self.tier,
            status=self.status,
            created_at=self.created_at,
            slang_submitted_count=self.slang_submitted_count,
            slang_approved_count=self.slang_approved_count,
        )


# API Models
class UserResponse(LingibleBaseModel):
    """API response model for user profile data."""

    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    username: str = Field(..., description="Username")
    tier: UserTier = Field(..., description="User tier")
    status: UserStatus = Field(..., description="Account status")

    created_at: datetime = Field(..., description="Account creation date")

    # Slang contribution statistics
    slang_submitted_count: int = Field(
        default=0, ge=0, description="Total slang terms submitted by user"
    )
    slang_approved_count: int = Field(
        default=0, ge=0, description="Total slang terms approved (auto or manual)"
    )


class UpgradeResponse(LingibleBaseModel):
    """Response model for user upgrade API."""

    success: bool = Field(..., description="Whether the upgrade was successful")
    message: str = Field(..., description="Success or error message")
    tier: str = Field(default="premium", description="User tier after upgrade")
    expires_at: datetime | None = Field(
        default=None, description="Subscription expiration date"
    )


class UserUsageResponse(LingibleBaseModel):
    """User usage API response - dynamic data, not cacheable."""

    tier: UserTier = Field(..., description="User tier (free/premium)")
    daily_limit: int = Field(..., description="Daily translation limit")
    daily_used: int = Field(..., description="Translations used today")
    daily_remaining: int = Field(..., description="Translations remaining today")
    reset_date: datetime = Field(..., description="Next daily reset date")

    # Limits data with clear names
    current_max_text_length: int = Field(
        ..., description="Maximum text length for user's current tier"
    )
    free_tier_max_length: int = Field(..., description="Free tier text length limit")
    premium_tier_max_length: int = Field(
        ..., description="Premium tier text length limit"
    )

    # Daily translation limits for comparison
    free_daily_limit: int = Field(..., description="Free tier daily translation limit")
    premium_daily_limit: int = Field(
        ..., description="Premium tier daily translation limit"
    )


class AccountDeletionRequest(LingibleBaseModel):
    """Request model for account deletion."""

    confirmation_text: str = Field(
        ..., description="User must type 'DELETE' to confirm"
    )
    reason: Optional[str] = Field(
        None, description="Optional reason for account deletion"
    )


class AccountDeletionResponse(LingibleBaseModel):
    """Response model for account deletion."""

    success: bool = Field(..., description="Whether the deletion was successful")
    message: str = Field(..., description="Confirmation message")
    deleted_at: datetime = Field(..., description="When the account was deleted")
    cleanup_summary: dict = Field(..., description="Summary of data cleanup performed")
